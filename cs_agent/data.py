from typing import Dict, Any, List
import csv
import os
import json
import glob
from langchain_core.documents import Document


def load_json_documents_from_dir(dir_path: str) -> List[Document]:
    docs: List[Document] = []  # 결과 문서 리스트 초기화
    for fp in glob.glob(os.path.join(dir_path, "*.json")):  # 디렉토리 내 모든 .json 파일 순회
        try:
            with open(fp, "r", encoding="utf-8") as f:  # JSON 파일 열기
                data = json.load(f)  # JSON 파싱
        except Exception:
            continue
        if isinstance(data, list):  # 배열(JSON list)인 경우 각 항목을 개별 문서로
            for i, item in enumerate(data):  # 인덱스 메타 포함
                text = json.dumps(item, ensure_ascii=False)  # dict → JSON 문자열화
                docs.append(
                    Document(
                        page_content=text,
                        metadata={
                            "source": os.path.basename(fp),
                            "index": i,
                            "category": "Transportation",
                        },
                    )
                )
        elif isinstance(data, dict):  # 단일 객체(JSON object)인 경우 한 문서로 처리
            text = json.dumps(data, ensure_ascii=False)  # dict → JSON 문자열화
            docs.append(  # 문서 리스트에 추가
                Document(
                    page_content=text,
                    metadata={
                        "source": os.path.basename(fp),
                        "category": "Transportation",
                    },
                )
            )
    return docs  # 변환된 문서 리스트 반환


def load_json_documents(file_paths: List[str]) -> List[Document]:
    docs: List[Document] = []  # 결과 문서 리스트
    for fp in file_paths:  # 전달된 파일 경로만 사용
        if not os.path.exists(fp):
            continue
        try:
            with open(fp, "r", encoding="utf-8") as f:  # JSON 파일 열기
                data = json.load(f)  # JSON 파싱
        except Exception:
            continue
        if isinstance(data, list):  # 배열(JSON list) 처리
            for i, item in enumerate(data):  # 항목별로 문서화
                text = json.dumps(item, ensure_ascii=False)  # dict → JSON 문자열화
                docs.append(
                    Document(
                        page_content=text,
                        metadata={
                            "source": os.path.basename(fp),
                            "index": i,
                            "category": "Transportation",
                        },
                    )
                )
        elif isinstance(data, dict):  # 단일 객체(JSON object) 처리
            text = json.dumps(data, ensure_ascii=False)  # dict → JSON 문자열화
            docs.append(  # 문서 리스트에 추가
                Document(
                    page_content=text,
                    metadata={
                        "source": os.path.basename(fp),
                        "category": "Transportation",
                    },
                )
            )
    return docs  # 변환된 문서 리스트 반환



# Auto-include two specific JSON files under project data directory
_project_root = os.path.dirname(os.path.dirname(__file__))
_data_dir = os.path.join(_project_root, "data")
_specific_json_files = [  # 임베딩 대상 JSON 파일 목록(두 개만 포함)
    os.path.join(_data_dir, "승하차정보.json"),  # 승하차 정보
    os.path.join(_data_dir, "통근수당.json"),  # 통근 수당 정보
]
_specific_docs = load_json_documents(_specific_json_files)

# Final knowledge base used by tools: ONLY specific JSON docs
knowledge_base_documents: List[Document] = _specific_docs  # 최종 KB: 두 JSON에서만 로드된 문서들


