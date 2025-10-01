from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import InMemorySaver
from langchain_upstage import ChatUpstage

from ..tools import search_knowledge_base, web_search


def create_simple_agent():
    checkpointer = InMemorySaver()
    llm = ChatUpstage(model="solar-pro2", temperature=0)
    agent = create_react_agent(
        model=llm,
        tools=[search_knowledge_base, web_search],
        prompt=(
            "You are a helpful customer support agent. Use the available tools to search the knowledge "
            "base and web for information to help customers."
        ),
        checkpointer=checkpointer,
    )
    return agent
