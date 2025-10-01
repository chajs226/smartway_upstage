from typing import Any, Dict, List
import json
import numpy as np
import faiss
from langchain_core.tools import tool
from tavily import TavilyClient
from datetime import datetime

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
