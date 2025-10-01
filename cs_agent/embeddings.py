from typing import List, Tuple
import numpy as np
import faiss
from openai import OpenAI
from langchain_core.documents import Document

from .config import build_openai_client
from .data import load_json_documents


def get_embeddings(client: OpenAI, texts: List[str], mode: str = "query") -> List[List[float]]:
    if mode == "query":
        model = "embedding-query"
    elif mode == "passage":
        model = "embedding-passage"
    else:
        raise ValueError("mode must be 'query' or 'passage'")
    resp = client.embeddings.create(model=model, input=texts)
    return [e.embedding for e in resp.data]


def build_faiss_index(docs: List[Document]) -> Tuple[faiss.IndexFlatIP, np.ndarray]:
    client = build_openai_client()
    texts = [d.page_content for d in docs]
    embeddings = get_embeddings(client, texts, mode="passage")
    matrix = np.array(embeddings).astype(np.float32)

    dim = len(embeddings[0]) if embeddings else 0
    index = faiss.IndexFlatIP(dim)
    faiss.normalize_L2(matrix)
    index.add(matrix)
    return index, matrix


def build_index_from_json_files(file_paths: List[str]) -> Tuple[faiss.IndexFlatIP, np.ndarray, List[Document]]:
    """Load JSON from given paths, convert to Documents, and build a FAISS index."""
    docs = load_json_documents(file_paths)
    index, matrix = build_faiss_index(docs)
    return index, matrix, docs
