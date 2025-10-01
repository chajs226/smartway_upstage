# 명령줄 인수 파싱을 위한 argparse 모듈 임포트
import argparse
# 시스템 관련 기능을 위한 sys 모듈 임포트
import sys
# LangGraph의 워크플로우 제어를 위한 Command 클래스 임포트
from langgraph.types import Command

# 단순 ReAct 에이전트 생성 함수 임포트
from cs_agent.agents.react_agent import create_simple_agent
# 고객 지원 워크플로우 생성 함수 임포트
#from cs_agent.workflows.customer_support import build_workflow


def run_react(question: str):
    """
    ReAct 에이전트를 실행하여 단일 질문에 답변하는 함수
    
    Args:
        question: 사용자의 질문 문자열
    """
    # 단순 ReAct 에이전트 인스턴스 생성
    agent = create_simple_agent()
    # 대화 스레드 ID를 포함한 설정 딕셔너리 생성
    config = {"configurable": {"thread_id": "1"}}
    # 에이전트에 사용자 질문을 전달하고 결과 받기
    result = agent.invoke({"messages": [{"role": "user", "content": question}]}, config)
    # 결과에서 메시지 리스트 추출 (없으면 빈 리스트)
    messages = result.get("messages", [])
    # 메시지가 존재하는 경우
    if messages:
        # 마지막 메시지 추출 (에이전트의 최종 응답)
        last = messages[-1]
        try:
            # 메시지 내용을 출력
            print(last.content)
        except Exception:
            # 내용 접근 실패 시 메시지 객체 전체를 문자열로 출력
            print(str(last))


def run_workflow():
    """
    대화형 고객 지원 워크플로우를 실행하는 함수
    사용자로부터 고객 ID와 질문을 순차적으로 입력받아 처리
    """
    # 고객 지원 워크플로우 그래프 생성
    graph = build_workflow()
    # 대화 스레드 ID를 포함한 설정 딕셔너리 생성
    config = {"configurable": {"thread_id": "1"}}

    # Step 1: 고객 ID 입력 프롬프트 트리거
    # 빈 메시지로 워크플로우 시작하여 ID 입력 요청 발생
    events = list(graph.stream({"messages": [("human", "")]}, stream_mode="updates", config=config))
    # 중단(interrupt) 이벤트에서 프롬프트 메시지 출력
    _print_interrupts(events)

    # 표준 입력(stdin)에서 고객 ID 읽기
    cust_id = input().strip()  # 앞뒤 공백 제거
    # 고객 ID를 Command로 전달하여 워크플로우 재개
    events = list(graph.stream(Command(resume=cust_id), stream_mode="updates", config=config))
    # 다음 중단 이벤트의 프롬프트 출력 (질문 입력 요청)
    _print_interrupts(events)

    # 표준 입력에서 사용자 질문 읽기
    question = input().strip()  # 앞뒤 공백 제거
    # 질문을 Command로 전달하여 워크플로우 재개 및 최종 처리
    events = list(graph.stream(Command(resume=question), stream_mode="updates", config=config))

    # 최종 어시스턴트 메시지 출력
    # 모든 이벤트 순회
    for ev in events:
        # LLM 노드의 출력 확인
        llm_out = ev.get("llm")
        # LLM 출력이 존재하고 메시지가 있는 경우
        if llm_out and "messages" in llm_out and llm_out["messages"]:
            # 마지막 메시지 추출
            msg = llm_out["messages"][-1]
            try:
                # 메시지 내용 출력
                print(msg.content)
            except Exception:
                # 실패 시 메시지 객체를 문자열로 출력
                print(str(msg))
        # 전문가 에스컬레이션 노드의 출력 확인
        esc = ev.get("escalate_to_specialist")
        # 에스컬레이션 출력이 존재하고 메시지가 있는 경우
        if esc and "messages" in esc and esc["messages"]:
            # 마지막 메시지 추출
            msg = esc["messages"][-1]
            try:
                # 메시지 내용 출력
                print(msg.content)
            except Exception:
                # 실패 시 메시지 객체를 문자열로 출력
                print(str(msg))


def _print_interrupts(events):
    """
    워크플로우 이벤트에서 중단(interrupt) 프롬프트를 추출하여 출력하는 헬퍼 함수
    
    Args:
        events: 워크플로우에서 발생한 이벤트 리스트
    """
    # 각 이벤트 순회
    for ev in events:
        # 이벤트에서 중단(interrupt) 데이터 추출
        intr = ev.get("__interrupt__")
        # 중단 데이터가 존재하는 경우
        if intr:
            # 중단 데이터가 튜플이면 첫 번째 요소의 value 속성 추출, 아니면 문자열로 변환
            prompt = intr[0].value if isinstance(intr, tuple) else str(intr)
            # 추출한 프롬프트 메시지 출력
            print(prompt)


def main(argv=None):
    """
    CLI 애플리케이션의 메인 진입점
    명령줄 인수를 파싱하고 적절한 실행 모드를 선택
    
    Args:
        argv: 명령줄 인수 리스트 (None이면 sys.argv 사용)
    """
    # ArgumentParser 객체 생성 (프로그램 설명 포함)
    parser = argparse.ArgumentParser(description="Customer Support Agent CLI")
    # 서브커맨드(하위 명령어) 파서 생성
    # dest="cmd": 선택된 서브커맨드를 'cmd' 변수에 저장
    # required=True: 서브커맨드 입력 필수
    sub = parser.add_subparsers(dest="cmd", required=True)

    # 'react' 서브커맨드 파서 추가 (단일 질문 처리 모드)
    p_react = sub.add_parser("react", help="Run prebuilt ReAct agent once")
    # --question 인수 추가 (필수 입력)
    p_react.add_argument("--question", required=True)

    # 'workflow' 서브커맨드 파서 추가 (대화형 워크플로우 모드)
    sub.add_parser("workflow", help="Run full workflow (interactive)")

    # 명령줄 인수 파싱 실행
    args = parser.parse_args(argv)

    # 선택된 서브커맨드에 따라 적절한 함수 실행
    if args.cmd == "react":
        # react 모드: 단일 질문으로 ReAct 에이전트 실행
        run_react(args.question)
    elif args.cmd == "workflow":
        # workflow 모드: 대화형 워크플로우 실행
        run_workflow()


# 스크립트가 직접 실행될 때만 main 함수 호출
if __name__ == "__main__":
    # sys.argv[1:]: 프로그램 이름을 제외한 명령줄 인수 전달
    main(sys.argv[1:])
