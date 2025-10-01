from typing import Any, Dict, List, Literal, Sequence, TypedDict, Annotated
import json

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_upstage import ChatUpstage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.types import interrupt
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import BaseModel

from ..tools import search_knowledge_base, web_search
from ..data import specialists


class GraphState(TypedDict):
    customer_question: str
    customer_id: str
    customer_context: str
    knowledge_base_results: List[Dict[str, Any]]
    web_search_raw_results: List[Dict[str, Any]]
    specialist_info: Dict[str, Any]
    messages: Annotated[List[BaseMessage], add_messages]


tools = [search_knowledge_base, web_search]
model = ChatUpstage(model="solar-pro2", temperature=0)
model_with_tools = model.bind_tools(tools)

def fetch_customer_context(customer_id: str) -> str:
    # Placeholder for demo; in a real impl, pull from CRM/store
    return f"Customer Information for {customer_id}:\nPlan: Premium\nStatus: active"


def get_customer_id(state: GraphState) -> Dict[str, Any]:
    customer_id = interrupt("🆔 Welcome to Customer Support! Can you please enter your Customer ID (CUSTXXX format)?")
    if not customer_id or not str(customer_id).startswith("CUST"):
        customer_id = interrupt(f"❌ Invalid format '{customer_id}'. Please enter your Customer ID in CUSTXXX format:")

    previous = state.get("customer_id", "")
    update = {"customer_id": customer_id}

    # reset search-related state for new session or new question
    update.update(
        {
            "knowledge_base_results": [],
            "web_search_raw_results": [],
            "specialist_info": {},
            "customer_question": "",
        }
    )

    # derive context
    customer_context = fetch_customer_context(customer_id)
    update["customer_context"] = customer_context
    return update


def get_customer_question(state: GraphState) -> Dict[str, Any]:
    question = interrupt("❓ Do you need any help? Please describe your issue or question:")
    if not question or len(str(question).strip()) < 5:
        question = interrupt("❓ Please provide more details about your issue:")
    return {"customer_question": str(question)}


def tool_node(state: GraphState) -> Dict[str, Any]:
    outputs = []
    update: Dict[str, Any] = {}
    last: AIMessage = state["messages"][-1]  # type: ignore
    for tool_call in last.tool_calls:
        name = tool_call["name"]
        args = tool_call["args"]
        if name == "search_knowledge_base":
            result = search_knowledge_base.invoke(args)
            update["knowledge_base_results"] = result if isinstance(result, list) else []
        elif name == "web_search":
            result = web_search.invoke(args)
            update["web_search_raw_results"] = result if isinstance(result, list) else []
        else:
            result = [{"error": f"Unknown tool {name}"}]
        outputs.append(
            ToolMessage(content=json.dumps(result), tool_call_id=tool_call["id"])  # type: ignore
        )
    update["messages"] = outputs
    return update


def llm_node(state: GraphState) -> Dict[str, Any]:
    customer_id = state.get("customer_id", "Unknown")
    customer_question = state.get("customer_question", "")
    customer_context = state.get("customer_context", "No customer context available")

    kb_results = state.get("knowledge_base_results", [])
    web_results = state.get("web_search_raw_results", [])
    has_tool_results = bool(kb_results or web_results)

    if has_tool_results:
        kb_context = []
        for r in kb_results:
            if isinstance(r, dict) and "content" in r:
                topic = r.get("topic", "Unknown")
                cat = r.get("category", "Unknown")
                score = r.get("score", 0.0)
                kb_context.append(f"- [{cat} - {topic}] (Score: {score:.1%}): {r.get('content','')}")
        web_context = []
        for r in web_results:
            if isinstance(r, dict) and "content" in r:
                title = r.get("title", "Untitled")
                score = r.get("score", 0.0)
                url = r.get("url", "")
                web_context.append(
                    f"- [{title}] (Score: {score:.1%}): {r.get('content','')}\n  Source: {url}"
                )
        system_text = (
            f"You are a Customer Service Assistant helping customer {customer_id}.\n\n"
            f"CUSTOMER CONTEXT:\n{customer_context}\n\nAVAILABLE INFORMATION:"
        )
        if kb_context:
            system_text += "\n\nKNOWLEDGE BASE RESULTS:\n" + "\n".join(kb_context)
        if web_context:
            system_text += "\n\nWEB SEARCH RESULTS:\n" + "\n".join(web_context)
        system_text += (
            f"\n\nCUSTOMER QUESTION: {customer_question}\n\nINSTRUCTIONS: Provide a comprehensive answer using the above information. "
            f"Cite sources when appropriate. Do NOT call tools."
        )
        system = SystemMessage(system_text)
    else:
        system = SystemMessage(
            "You are a Customer Service Assistant. Available tools: search_knowledge_base, web_search.\n"
            f"Customer context: {customer_context}\n"
            f"Customer question: '{customer_question}'\n"
            "If needed, call tools; otherwise provide a complete helpful answer."
        )

    response = model_with_tools.invoke([system, HumanMessage(content=customer_question)])
    return {"messages": [response]}


def tools_condition(state: GraphState) -> Literal["tools", "end", "escalate_to_specialist"]:
    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"
    # evaluate quality for optional escalation
    kb = state.get("knowledge_base_results", [])
    web = state.get("web_search_raw_results", [])
    kb_scores = [r.get("score", 0.0) for r in kb if isinstance(r, dict)]
    web_scores = [r.get("score", 0.0) for r in web if isinstance(r, dict)]
    max_kb = max(kb_scores) if kb_scores else 0.0
    max_web = max(web_scores) if web_scores else 0.0
    if (kb or web) and (max_kb < 0.25 and max_web < 0.5):
        return "escalate_to_specialist"
    return "end"


class InquiryCategorySchema(BaseModel):
    category: Literal["Technical", "Billing", "Account", "General", "Urgent"]


def classify_inquiry(customer_question: str) -> str:
    llm = ChatUpstage(model="solar-pro2", temperature=0)
    llm_structured = llm.with_structured_output(InquiryCategorySchema)
    prompt = (
        "Classify the following customer inquiry into one of: Technical, Billing, Account, General, Urgent.\n"
        f"Question: {customer_question}"
    )
    res = llm_structured.invoke(prompt)
    return res.category


def escalate_to_specialist(state: GraphState) -> Dict[str, Any]:
    question = state.get("customer_question", "")
    cat = classify_inquiry(question)
    spec = specialists.get(cat, specialists["General"])  # type: ignore
    msg = HumanMessage(
        content=(
            "I couldn't find sufficient information. Escalating your case to our specialist team.\n\n"
            f"🏷️ Assigned Specialist: {spec.get('specialist','Unknown')}\n"
            f"📧 Email: {spec.get('email','Unknown')}\n"
            f"🎯 Expertise: {', '.join(spec.get('expertise', ['General Support']))}\n"
            f"⏱️ Expected Response Time: {spec.get('response_time','Unknown')}\n"
        )
    )
    return {"specialist_info": spec, "messages": [msg]}


def build_workflow():
    builder = StateGraph(GraphState)
    builder.add_node("get_customer_id", get_customer_id)
    builder.add_node("get_customer_question", get_customer_question)
    builder.add_node("llm", llm_node)
    builder.add_node("tools", tool_node)
    builder.add_node("escalate_to_specialist", escalate_to_specialist)
    builder.set_entry_point("get_customer_id")
    builder.add_edge("get_customer_id", "get_customer_question")
    builder.add_edge("get_customer_question", "llm")
    builder.add_conditional_edges("llm", tools_condition, {
        "tools": "tools",
        "end": END,
        "escalate_to_specialist": "escalate_to_specialist",
    })
    builder.add_edge("tools", "llm")
    builder.add_edge("escalate_to_specialist", END)
    checkpointer = InMemorySaver()
    return builder.compile(checkpointer=checkpointer)
