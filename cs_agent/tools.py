from typing import Any, Dict, List, Literal  # 타입 힌팅을 위한 모듈
import json  # JSON 처리
import numpy as np  # 수치 계산
import faiss  # 벡터 유사도 검색
from langchain_core.tools import tool  # LangChain 도구 데코레이터
from tavily import TavilyClient  # 웹 검색 클라이언트
from datetime import datetime  # 날짜/시간 처리
import pandas as pd  # 데이터 분석
# matplotlib 백엔드를 non-interactive 모드로 설정 (GUI 없이 파일 저장만 수행)
import matplotlib
matplotlib.use('Agg')  # 메인 스레드 오류 방지를 위해 GUI 없는 백엔드 사용
import matplotlib.pyplot as plt  # 차트 생성
import seaborn as sns  # 고급 시각화
import os  # 파일/디렉토리 관리
from pydantic import BaseModel, Field  # 데이터 스키마 정의

from .config import build_openai_client, get_tavily_api_key  # 임베딩/LLM 클라이언트 빌더
from .data import knowledge_base_documents  # 두 JSON만 포함된 KB 문서
from .embeddings import get_embeddings  # 임베딩 생성 유틸

_index: faiss.IndexFlatIP | None = None  # 전역 FAISS 인덱스 핸들
_doc_matrix = None  # 전역 문서 임베딩 행렬
_docs = knowledge_base_documents  # 색인 대상 문서(두 JSON에서 로드)


def _ensure_index():
    global _index, _doc_matrix
    if _index is not None:
        return  # 이미 인덱스 초기화됨

    client = build_openai_client()  # 임베딩 생성 클라이언트
    texts = [d.page_content for d in _docs]  # 문서 본문 텍스트 수집
    vecs = get_embeddings(client, texts, mode="passage")  # 문서 임베딩 생성
    _doc_matrix = np.array(vecs).astype(np.float32)  # numpy 행렬로 변환
    dim = len(vecs[0]) if vecs else 0  # 벡터 차원 계산
    _index = faiss.IndexFlatIP(dim)  # 내적 기반 인덱스 생성
    faiss.normalize_L2(_doc_matrix)  # 코사인 유사도 동치 위해 정규화
    _index.add(_doc_matrix)  # 인덱스에 문서 벡터 추가


@tool
def search_knowledge_base(query: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """Search the internal knowledge base using vector similarity."""
    if not query or not str(query).strip():  # 입력 검증
        return [{"error": "query is required"}]

    _ensure_index()  # 인덱스 준비(두 JSON만 임베딩됨)
    client = build_openai_client()  # 질의 임베딩 클라이언트
    q_emb = get_embeddings(client, [query], mode="query")[0]  # 질의 텍스트 임베딩
    q_vec = np.array([q_emb]).astype(np.float32)  # numpy 행렬로 변환
    faiss.normalize_L2(q_vec)  # L2 정규화

    scores, idxs = _index.search(q_vec, k=max(1, int(top_k)))  # 유사도 검색  # type: ignore

    results: List[Dict[str, Any]] = []
    for i, (score, idx) in enumerate(zip(scores[0], idxs[0])):  # 상위 k 결과 순회
        if idx < len(_docs):  # 유효 범위 검사
            doc = _docs[idx]
            results.append(
                {
                    "content": doc.page_content,  # 문서 내용(JSON 문자열)
                    "score": float(score),  # 유사도 점수
                    "topic": doc.metadata.get("topic", "General"),  # 토픽(있다면)
                    "category": doc.metadata.get("category", "N/A"),  # 카테고리
                    "index": int(idx),  # 인덱스 내 위치
                    "rank": i + 1,  # 순위
                }
            )
    if not results:
        return [{"message": "No relevant information found in the knowledge base."}]
    return results  # 검색 결과 반환


def _rewrite_query_for_search(query: str) -> str:
    client = build_openai_client()
    try:
        current_date = datetime.now().strftime("%Y-%m-%d")
        rewrite_prompt = f"""
        You are an expert query optimizer. Transform the user question into a concise keyword query.
        Keep under 10 words. Use current date context if time-sensitive: {current_date}.
        Return ONLY the rewritten query string.

        User question: {query}
        """
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "search_query_suggestions",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {"rewritten_query": {"type": "string"}},
                    "required": ["rewritten_query"],
                },
            },
        }
        resp = client.chat.completions.create(
            model="solar-pro2",
            messages=[{"role": "system", "content": rewrite_prompt}],
            response_format=response_format,
        )
        obj = json.loads(resp.choices[0].message.content)
        return obj.get("rewritten_query", query)
    except Exception:
        return query


@tool
def web_search(query: str, max_results: int = 3, rewrite_mode: bool = True) -> List[Dict[str, Any]]:
    """Search the web using Tavily for current information."""
    try:
        api_key = get_tavily_api_key()
        tavily = TavilyClient(api_key=api_key) if api_key else TavilyClient()
        search_query = _rewrite_query_for_search(query) if rewrite_mode else query
        resp = tavily.search(
            query=search_query,
            search_depth="basic",
            max_results=max_results,
            include_domains=[],
            exclude_domains=[],
        )
        if not resp.get("results"):
            return [{"message": "No relevant web search results found."}]
        results: List[Dict[str, Any]] = []
        for i, r in enumerate(resp["results"], 1):
            results.append(
                {
                    "title": r.get("title", "Untitled"),
                    "content": r.get("content", "No content available"),
                    "url": r.get("url", ""),
                    "score": float(r.get("score", 0.0)),
                    "rank": i,
                    "query": search_query,
                }
            )
        return results
    except Exception as e:
        return [{"error": f"Web search error: {str(e)}"}]


# ============================================================================
# 데이터 분석 및 차트 생성 기능
# ============================================================================

class ChartTypeSchema(BaseModel):
    """
    LLM이 분석 질문에 적합한 차트 타입을 결정하기 위한 스키마
    """
    # 차트 타입: 막대, 선, 파이, 산점도, 히트맵, 표
    chart_type: Literal["bar", "line", "pie", "scatter", "heatmap", "table"] = Field(
        description="적절한 차트 타입 선택"
    )
    # 차트 선택 이유
    reason: str = Field(
        description="왜 이 차트 타입이 적절한지 설명"
    )
    # X축에 사용할 컬럼명
    x_axis: str | None = Field(
        default=None,
        description="X축 데이터 컬럼명 (카테고리 또는 시간)"
    )
    # Y축에 사용할 컬럼명
    y_axis: str | None = Field(
        default=None,
        description="Y축 데이터 컬럼명 (수치 값)"
    )
    # 데이터 집계 방법
    aggregation: Literal["sum", "count", "average", "min", "max"] | None = Field(
        default=None,
        description="데이터 집계 방법"
    )


def _extract_structured_data(search_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    search_knowledge_base 결과에서 JSON 문자열을 파싱하여 구조화된 데이터 추출
    
    Args:
        search_results: search_knowledge_base 함수의 반환값 (문서 리스트)
    
    Returns:
        구조화된 데이터 딕셔너리 리스트
    """
    structured_data = []  # 추출된 구조화 데이터를 저장할 리스트
    
    # 각 검색 결과 순회
    for result in search_results:
        # 결과에서 content 필드 추출 (JSON 문자열)
        content = result.get("content", "")
        try:
            # JSON 문자열을 파이썬 객체로 파싱
            parsed = json.loads(content)
            
            # 파싱 결과가 리스트인 경우 (여러 항목)
            if isinstance(parsed, list):
                # 모든 항목을 구조화 데이터에 추가
                structured_data.extend(parsed)
            # 파싱 결과가 딕셔너리인 경우 (단일 항목)
            elif isinstance(parsed, dict):
                # 해당 항목을 구조화 데이터에 추가
                structured_data.append(parsed)
                
        except json.JSONDecodeError:
            # JSON 파싱 실패 시 해당 결과 무시하고 다음으로
            continue
    
    # 추출된 모든 구조화 데이터 반환
    return structured_data


def _decide_chart_type(query: str, df: pd.DataFrame) -> ChartTypeSchema:
    """
    LLM을 사용해 질문과 데이터를 분석하여 적절한 차트 타입 결정
    
    Args:
        query: 사용자의 분석 질문
        df: 분석할 DataFrame
    
    Returns:
        차트 타입과 축, 집계 방법이 포함된 스키마
    """
    
    # DataFrame의 각 컬럼에 대한 메타 정보 생성
    columns_info = {
        col: {
            "dtype": str(df[col].dtype),  # 데이터 타입 (int, float, object 등)
            "sample": df[col].head(3).tolist(),  # 상위 3개 샘플 데이터
            "unique_count": df[col].nunique()  # 고유값 개수
        }
        for col in df.columns  # 모든 컬럼에 대해
    }
    
    # LLM에게 전달할 프롬프트 구성
    prompt = f"""
    분석 질문: {query}
    
    사용 가능한 데이터:
    {json.dumps(columns_info, ensure_ascii=False, indent=2)}
    
    다음 기준으로 최적의 차트 타입을 선택하세요:
    - bar: 카테고리별 비교 (예: 노선별 승차 인원, 부서별 예산)
    - line: 시간에 따른 추세 (예: 월별 통근수당 변화, 일별 방문자 수)
    - pie: 전체 대비 비율 (예: 전체 예산 중 각 부서 비율)
    - scatter: 두 변수 간 상관관계 (예: 거리와 수당의 관계)
    - heatmap: 2차원 매트릭스 패턴 (예: 시간대별/요일별 패턴)
    - table: 정확한 수치가 중요하거나 복잡한 경우
    
    x축, y축에 사용할 컬럼명과 집계 방법(sum, count, average, min, max)도 함께 결정하세요.
    컬럼명은 위 데이터에 실제 존재하는 컬럼만 사용하세요.
    """
    
    # Structured Output을 위한 LLM 설정
    from langchain_upstage import ChatUpstage
    llm_structured = ChatUpstage(model="solar-pro2", temperature=0)  # 결정론적 출력
    # 스키마를 강제하는 LLM 래퍼 생성
    llm_with_schema = llm_structured.with_structured_output(ChartTypeSchema)
    
    # LLM 호출 및 결과 반환
    result = llm_with_schema.invoke(prompt)
    return result


def _aggregate_data(
    df: pd.DataFrame,
    x_axis: str | None,
    y_axis: str | None,
    aggregation: str | None
) -> pd.DataFrame:
    """
    지정된 축과 집계 방법으로 데이터 처리
    
    Args:
        df: 원본 DataFrame
        x_axis: 그룹화할 컬럼 (X축)
        y_axis: 집계할 컬럼 (Y축)
        aggregation: 집계 방법
    
    Returns:
        집계된 DataFrame
    """
    # X축 또는 Y축이 지정되지 않은 경우 원본 반환
    if not x_axis or not y_axis:
        return df
    
    # 집계 방법에 따라 처리
    if aggregation == "count":
        # 개수 집계: x_axis로 그룹화하여 y_axis 개수 계산
        return df.groupby(x_axis)[y_axis].count().reset_index()
    elif aggregation == "sum":
        # 합계 집계: x_axis로 그룹화하여 y_axis 합계 계산
        return df.groupby(x_axis)[y_axis].sum().reset_index()
    elif aggregation == "average":
        # 평균 집계: x_axis로 그룹화하여 y_axis 평균 계산
        return df.groupby(x_axis)[y_axis].mean().reset_index()
    elif aggregation == "min":
        # 최소값 집계: x_axis로 그룹화하여 y_axis 최소값 계산
        return df.groupby(x_axis)[y_axis].min().reset_index()
    elif aggregation == "max":
        # 최대값 집계: x_axis로 그룹화하여 y_axis 최대값 계산
        return df.groupby(x_axis)[y_axis].max().reset_index()
    
    # 집계 방법이 지정되지 않은 경우 원본 반환
    return df


def _create_chart(
    data: pd.DataFrame,
    chart_type: str,
    title: str
) -> str:
    """
    데이터와 차트 타입에 맞는 시각화 생성
    
    Args:
        data: 시각화할 DataFrame
        chart_type: 차트 타입 (bar, line, pie 등)
        title: 차트 제목
    
    Returns:
        생성된 차트 파일의 경로
    """
    # 차트 크기 설정 (가로 10인치, 세로 6인치)
    plt.figure(figsize=(10, 6))
    
    # 한글 폰트 설정 (macOS 기준)
    plt.rcParams['font.family'] = 'AppleGothic'
    # 마이너스 기호 깨짐 방지
    plt.rcParams['axes.unicode_minus'] = False
    
    # 차트 타입에 따라 다른 시각화 생성
    if chart_type == "bar":
        # 막대 그래프: 첫 번째 컬럼(X축)과 두 번째 컬럼(Y축) 사용
        plt.bar(data.iloc[:, 0], data.iloc[:, 1])
        plt.xlabel(data.columns[0])  # X축 레이블
        plt.ylabel(data.columns[1])  # Y축 레이블
        plt.xticks(rotation=45, ha='right')  # X축 레이블 45도 회전
        
    elif chart_type == "line":
        # 선 그래프: 추세선 + 데이터 포인트 표시
        plt.plot(data.iloc[:, 0], data.iloc[:, 1], marker='o')
        plt.xlabel(data.columns[0])  # X축 레이블
        plt.ylabel(data.columns[1])  # Y축 레이블
        plt.xticks(rotation=45, ha='right')  # X축 레이블 45도 회전
        
    elif chart_type == "pie":
        # 파이 차트: 비율 표시 (자동으로 퍼센트 계산)
        plt.pie(data.iloc[:, 1], labels=data.iloc[:, 0], autopct='%1.1f%%')
        
    elif chart_type == "scatter":
        # 산점도: 두 변수 간 관계 표시
        plt.scatter(data.iloc[:, 0], data.iloc[:, 1])
        plt.xlabel(data.columns[0])  # X축 레이블
        plt.ylabel(data.columns[1])  # Y축 레이블
        
    elif chart_type == "heatmap":
        # 히트맵: 2차원 데이터의 패턴 표시
        # 3개 이상의 컬럼이 필요 (행, 열, 값)
        if len(data.columns) >= 3:
            # 피벗 테이블 생성
            pivot = data.pivot_table(
                values=data.columns[2],  # 값으로 사용할 컬럼
                index=data.columns[0],   # 행으로 사용할 컬럼
                columns=data.columns[1]  # 열로 사용할 컬럼
            )
            # 히트맵 그리기 (값 표시, 소수점 없이)
            sns.heatmap(pivot, annot=True, fmt='.0f', cmap='YlOrRd')
        else:
            # 컬럼이 부족한 경우 기본 히트맵
            sns.heatmap(data.select_dtypes(include=[np.number]), annot=True)
    
    # 차트 제목 설정
    plt.title(title)
    # 레이아웃 자동 조정 (레이블 잘림 방지)
    plt.tight_layout()
    
    # 차트를 저장할 디렉토리 생성
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")  # 현재 시각 (파일명 중복 방지)
    chart_dir = "generated_charts"  # 차트 저장 디렉토리
    os.makedirs(chart_dir, exist_ok=True)  # 디렉토리가 없으면 생성
    
    # 차트 파일 경로 생성
    chart_path = f"{chart_dir}/chart_{timestamp}.png"
    # 차트를 PNG 파일로 저장 (고해상도 150dpi, 여백 최소화)
    plt.savefig(chart_path, dpi=150, bbox_inches='tight')
    # 메모리에서 차트 객체 제거 (다음 차트를 위해)
    plt.close()
    
    # 저장된 차트 파일 경로 반환
    return chart_path


@tool
def analyze_and_visualize(query: str) -> str:
    """
    Analyze data from knowledge base and create appropriate visualization chart.
    
    This tool:
    1. Searches knowledge base for relevant data
    2. Extracts and structures the data
    3. Uses LLM to determine the best chart type
    4. Aggregates data appropriately
    5. Creates and saves the visualization
    
    Args:
        query: Analysis question (e.g., "노선별 승차 인원 비교", "월별 통근수당 추이")
    
    Returns:
        A message with chart path and analysis summary
    """
    
    # Step 1: 지식 베이스에서 관련 데이터 검색
    search_results = search_knowledge_base.invoke({"query": query, "top_k": 5})
    
    # 검색 결과가 없거나 에러인 경우 처리
    if not search_results or "error" in search_results[0]:
        return "데이터를 찾을 수 없습니다. 다른 질문을 시도해주세요."
    
    # Step 2: 검색 결과를 구조화된 데이터로 변환
    structured_data = _extract_structured_data(search_results)
    
    # 구조화된 데이터가 없는 경우
    if not structured_data:
        return "분석 가능한 구조화된 데이터를 찾을 수 없습니다."
    
    # Step 3: DataFrame으로 변환
    try:
        df = pd.DataFrame(structured_data)
    except Exception as e:
        return f"데이터 변환 중 오류 발생: {str(e)}"
    
    # DataFrame이 비어있는 경우
    if df.empty:
        return "데이터가 비어있습니다."
    
    # Step 4: LLM을 사용해 적절한 차트 타입 결정
    try:
        chart_decision = _decide_chart_type(query, df)
    except Exception as e:
        return f"차트 타입 결정 중 오류 발생: {str(e)}"
    
    # Step 5: 데이터 집계 (필요한 경우)
    try:
        aggregated_data = _aggregate_data(
            df,
            chart_decision.x_axis,
            chart_decision.y_axis,
            chart_decision.aggregation
        )
    except Exception as e:
        return f"데이터 집계 중 오류 발생: {str(e)}"
    
    # Step 6: 차트 생성
    try:
        chart_path = _create_chart(
            aggregated_data,
            chart_decision.chart_type,
            query
        )
    except Exception as e:
        return f"차트 생성 중 오류 발생: {str(e)}"
    
    # Step 7: 결과 메시지 생성
    result_message = f"""
분석 완료!

📊 차트 타입: {chart_decision.chart_type}
💡 선택 이유: {chart_decision.reason}
📁 차트 저장 위치: {chart_path}

집계된 데이터:
{aggregated_data.to_string(index=False)}
"""
    
    return result_message
