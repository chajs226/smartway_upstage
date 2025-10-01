import argparse
import sys
from langgraph.types import Command

from cs_agent.agents.react_agent import create_simple_agent
from cs_agent.workflows.customer_support import build_workflow


def run_react(question: str):
    agent = create_simple_agent()
    config = {"configurable": {"thread_id": "1"}}
    result = agent.invoke({"messages": [{"role": "user", "content": question}]}, config)
    messages = result.get("messages", [])
    if messages:
        last = messages[-1]
        try:
            print(last.content)
        except Exception:
            print(str(last))


def run_workflow():
    graph = build_workflow()
    config = {"configurable": {"thread_id": "1"}}

    # Step 1: trigger ID prompt
    events = list(graph.stream({"messages": [("human", "")]}, stream_mode="updates", config=config))
    _print_interrupts(events)

    # Read customer id from stdin
    cust_id = input().strip()
    events = list(graph.stream(Command(resume=cust_id), stream_mode="updates", config=config))
    _print_interrupts(events)

    # Read question from stdin
    question = input().strip()
    events = list(graph.stream(Command(resume=question), stream_mode="updates", config=config))

    # Print final assistant message
    for ev in events:
        llm_out = ev.get("llm")
        if llm_out and "messages" in llm_out and llm_out["messages"]:
            msg = llm_out["messages"][-1]
            try:
                print(msg.content)
            except Exception:
                print(str(msg))
        esc = ev.get("escalate_to_specialist")
        if esc and "messages" in esc and esc["messages"]:
            msg = esc["messages"][-1]
            try:
                print(msg.content)
            except Exception:
                print(str(msg))


def _print_interrupts(events):
    for ev in events:
        intr = ev.get("__interrupt__")
        if intr:
            # print prompt
            prompt = intr[0].value if isinstance(intr, tuple) else str(intr)
            print(prompt)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Customer Support Agent CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_react = sub.add_parser("react", help="Run prebuilt ReAct agent once")
    p_react.add_argument("--question", required=True)

    sub.add_parser("workflow", help="Run full workflow (interactive)")

    args = parser.parse_args(argv)

    if args.cmd == "react":
        run_react(args.question)
    elif args.cmd == "workflow":
        run_workflow()


if __name__ == "__main__":
    main(sys.argv[1:])
