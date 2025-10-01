from typing import Any, Dict, List
import json
import numpy as np
import faiss
from langchain_core.tools import tool
from tavily import TavilyClient
from datetime import datetime

from .config import build_openai_client, get_tavily_api_key
from .data import knowledge_base_documents
from .embeddings import get_embeddings

_index: faiss.IndexFlatIP | None = None
_doc_matrix = None
_docs = knowledge_base_documents


def _ensure_index():
    global _index, _doc_matrix
    if _index is not None:
        return

    client = build_openai_client()
    texts = [d.page_content for d in _docs]
    vecs = get_embeddings(client, texts, mode="passage")
    _doc_matrix = np.array(vecs).astype(np.float32)
    dim = len(vecs[0]) if vecs else 0
    _index = faiss.IndexFlatIP(dim)
    faiss.normalize_L2(_doc_matrix)
    _index.add(_doc_matrix)


@tool
def search_knowledge_base(query: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """Search the internal knowledge base using vector similarity."""
    if not query or not str(query).strip():
        return [{"error": "query is required"}]

    _ensure_index()
    client = build_openai_client()
    q_emb = get_embeddings(client, [query], mode="query")[0]
    q_vec = np.array([q_emb]).astype(np.float32)
    faiss.normalize_L2(q_vec)

    scores, idxs = _index.search(q_vec, k=max(1, int(top_k)))  # type: ignore

    results: List[Dict[str, Any]] = []
    for i, (score, idx) in enumerate(zip(scores[0], idxs[0])):
        if idx < len(_docs):
            doc = _docs[idx]
            results.append(
                {
                    "content": doc.page_content,
                    "score": float(score),
                    "topic": doc.metadata.get("topic", "General"),
                    "category": doc.metadata.get("category", "N/A"),
                    "index": int(idx),
                    "rank": i + 1,
                }
            )
    if not results:
        return [{"message": "No relevant information found in the knowledge base."}]
    return results


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
