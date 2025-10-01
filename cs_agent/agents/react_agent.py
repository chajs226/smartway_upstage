# LangGraph의 사전 빌드된 ReAct 에이전트 생성 함수 임포트
from langgraph.prebuilt import create_react_agent
# 인메모리 체크포인터 (대화 상태 저장용)
from langgraph.checkpoint.memory import InMemorySaver
# Upstage의 ChatUpstage LLM
from langchain_upstage import ChatUpstage

# 도구 함수들 임포트: 지식베이스 검색, 웹 검색, 분석 및 시각화
from ..tools import search_knowledge_base, web_search, analyze_and_visualize


def create_simple_agent():
    """
    데이터 분석 및 시각화 기능을 갖춘 고객 지원 ReAct 에이전트 생성
    
    Returns:
        설정된 ReAct 에이전트 인스턴스
    """
    # 인메모리 체크포인터 생성 (대화 컨텍스트 유지)
    checkpointer = InMemorySaver()
    
    # Upstage Solar-Pro2 LLM 초기화 (temperature=0으로 결정론적 응답)
    llm = ChatUpstage(model="solar-pro2", temperature=0)
    
    # ReAct 에이전트 생성
    agent = create_react_agent(
        model=llm,  # 사용할 LLM
        # 사용 가능한 도구 목록:
        # - search_knowledge_base: 내부 지식베이스에서 정보 검색
        # - analyze_and_visualize: 데이터 분석 및 차트 생성
        tools=[search_knowledge_base, analyze_and_visualize],
        # 에이전트 시스템 프롬프트 (역할 정의)
        prompt=(
            "You are a helpful customer support agent with data analysis capabilities. "
            "You can:\n"
            "1. Search the knowledge base for information using 'search_knowledge_base'\n"
            "2. Analyze data and create visualizations using 'analyze_and_visualize'\n"
            "\n"
            "When users ask analytical questions (like comparing data, showing trends, etc.), "
            "use the analyze_and_visualize tool to create appropriate charts.\n"
            "For general information queries, use search_knowledge_base.\n"
            "\n"
            "Always provide clear, helpful responses in Korean."
        ),
        checkpointer=checkpointer,  # 대화 상태 저장소
    )
    
    # 생성된 에이전트 반환
    return agent
