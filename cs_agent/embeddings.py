from typing import List, Tuple
import numpy as np
import faiss
from openai import OpenAI
from langchain_core.documents import Document

from .config import build_openai_client
from .data import load_json_documents


def get_embeddings(client: OpenAI, texts: List[str], mode: str = "query") -> List[List[float]]:
    if mode == "query":
        model = "embedding-query"  # 질의용 임베딩 모델
    elif mode == "passage":
        model = "embedding-passage"  # 문서용 임베딩 모델
    else:
        raise ValueError("mode must be 'query' or 'passage'")  # 잘못된 모드 예외
    resp = client.embeddings.create(model=model, input=texts)  # 임베딩 API 호출
    return [e.embedding for e in resp.data]  # 벡터 리스트 반환


def build_faiss_index(docs: List[Document]) -> Tuple[faiss.IndexFlatIP, np.ndarray]:
    client = build_openai_client()  # OpenAI(Upstage) 클라이언트 생성
    texts = [d.page_content for d in docs]  # 문서 본문 텍스트 추출
    embeddings = get_embeddings(client, texts, mode="passage")  # 문서 임베딩 생성
    matrix = np.array(embeddings).astype(np.float32)  # 임베딩을 numpy 행렬로 변환

    dim = len(embeddings[0]) if embeddings else 0  # 벡터 차원 계산
    index = faiss.IndexFlatIP(dim)  # 내적 기반 인덱스 생성
    faiss.normalize_L2(matrix)  # 코사인 유사도 동치 계산을 위한 L2 정규화
    index.add(matrix)  # 문서 임베딩을 인덱스에 추가
    return index, matrix  # 인덱스와 행렬 반환


def build_index_from_json_files(file_paths: List[str]) -> Tuple[faiss.IndexFlatIP, np.ndarray, List[Document]]:
    """Load JSON from given paths, convert to Documents, and build a FAISS index."""
    docs = load_json_documents(file_paths)  # JSON → Documents 변환
    index, matrix = build_faiss_index(docs)  # FAISS 인덱스/행렬 생성
    return index, matrix, docs  # 인덱스, 행렬, 문서 반환
