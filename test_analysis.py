#!/usr/bin/env python3
"""
데이터 분석 및 차트 생성 기능 테스트 스크립트

사용법:
    python test_analysis.py
"""

from cs_agent.agents.react_agent import create_simple_agent


def test_analysis_questions():
    """
    다양한 분석 질문으로 에이전트 테스트
    """
    # 에이전트 생성
    agent = create_simple_agent()
    # 설정 (스레드 ID 지정)
    config = {"configurable": {"thread_id": "test-1"}}
    
    # 테스트할 질문 목록
    test_questions = [
        # 막대 그래프가 적절한 질문 (카테고리별 비교)
        "노선별 승차 인원을 비교해서 막대 그래프로 보여줘",
        
        # 선 그래프가 적절한 질문 (시간별 추세)
        "출발시간대별 통근수당 추이를 선 그래프로 보여줘",
        
        # 파이 차트가 적절한 질문 (비율)
        "각 노선의 운행거리 비율을 파이 차트로 보여줘",
        
        # 일반 정보 검색 (차트 불필요)
        "업스테이지 셔틀버스의 승하차 인원이 많은 노선 순으로 알려줘",
    ]
    
    print("=" * 80)
    print("데이터 분석 및 차트 생성 테스트")
    print("=" * 80)
    
    # 각 질문 테스트
    for i, question in enumerate(test_questions, 1):
        print(f"\n\n[테스트 {i}] 질문: {question}")
        print("-" * 80)
        
        try:
            # 에이전트에 질문 전달
            result = agent.invoke(
                {"messages": [{"role": "user", "content": question}]},
                config
            )
            
            # 응답 메시지 추출
            messages = result.get("messages", [])
            if messages:
                last_message = messages[-1]
                print(f"\n응답:\n{last_message.content}")
            else:
                print("\n응답 없음")
                
        except Exception as e:
            print(f"\n오류 발생: {str(e)}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("테스트 완료!")
    print("=" * 80)


if __name__ == "__main__":
    test_analysis_questions()
