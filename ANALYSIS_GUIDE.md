# 데이터 분석 및 차트 생성 기능 가이드

## 개요

이 프로젝트에 추가된 데이터 분석 및 차트 생성 기능은 사용자의 질문에 따라 자동으로 적절한 차트를 생성합니다.

## 주요 기능

### 1. 자동 차트 타입 선택
LLM이 질문의 의도와 데이터 구조를 분석하여 다음 중 최적의 차트를 선택합니다:

- **막대 그래프 (bar)**: 카테고리별 비교
  - 예: "노선별 승차 인원 비교해줘"
  
- **선 그래프 (line)**: 시간에 따른 추세
  - 예: "월별 통근수당 추이를 보여줘"
  
- **파이 차트 (pie)**: 전체 대비 비율
  - 예: "각 노선의 운행거리 비율을 알려줘"
  
- **산점도 (scatter)**: 두 변수 간 상관관계
  - 예: "운행거리와 수당의 관계를 분석해줘"
  
- **히트맵 (heatmap)**: 2차원 패턴 분석
  - 예: "시간대별/노선별 승차 패턴을 보여줘"
  
- **표 (table)**: 정확한 수치가 필요한 경우
  - 예: "각 노선의 상세 정보를 표로 보여줘"

### 2. 자동 데이터 집계
LLM이 결정한 방법으로 자동 집계:
- **sum**: 합계
- **count**: 개수
- **average**: 평균
- **min**: 최소값
- **max**: 최대값

## 사용 방법

### CLI로 사용하기

```bash
# ReAct 모드로 분석 질문
python cli.py react --question "노선별 승차 인원을 비교해줘"

# 워크플로우 모드로 대화형 분석
python cli.py workflow
```

### Python 코드에서 사용하기

```python
from cs_agent.agents.react_agent import create_simple_agent

# 에이전트 생성
agent = create_simple_agent()
config = {"configurable": {"thread_id": "1"}}

# 분석 질문
result = agent.invoke(
    {"messages": [{"role": "user", "content": "노선별 승차 인원 비교해줘"}]},
    config
)

# 응답 확인
print(result["messages"][-1].content)
```

## 아키텍처

### 처리 흐름

```
사용자 질문
    ↓
search_knowledge_base (도구)
    ↓ (데이터 검색)
analyze_and_visualize (도구)
    ↓
1. 구조화된 데이터 추출
2. LLM이 차트 타입 결정
3. 데이터 집계
4. 차트 생성
    ↓
결과 반환 (차트 경로 + 분석 요약)
```

### 주요 컴포넌트

#### 1. `ChartTypeSchema` (Pydantic 모델)
```python
class ChartTypeSchema(BaseModel):
    chart_type: Literal["bar", "line", "pie", "scatter", "heatmap", "table"]
    reason: str  # 차트 선택 이유
    x_axis: str | None  # X축 컬럼명
    y_axis: str | None  # Y축 컬럼명
    aggregation: Literal["sum", "count", "average", "min", "max"] | None
```

#### 2. `_extract_structured_data()`
- 검색 결과에서 JSON 문자열 파싱
- 리스트/딕셔너리를 평탄화된 데이터로 변환

#### 3. `_decide_chart_type()`
- LLM Structured Output 사용
- 질문과 데이터 컬럼 정보를 분석
- 최적의 차트 타입 + 축 + 집계 방법 결정

#### 4. `_aggregate_data()`
- pandas groupby를 사용한 데이터 집계
- sum, count, average, min, max 지원

#### 5. `_create_chart()`
- matplotlib/seaborn으로 차트 생성
- 한글 폰트 지원 (AppleGothic)
- PNG 파일로 저장 (generated_charts/ 디렉토리)

#### 6. `analyze_and_visualize` (Tool)
- 전체 파이프라인 orchestration
- 에러 핸들링 및 사용자 친화적 메시지 반환

## 예제 질문들

### 승하차 데이터 분석
```python
questions = [
    "노선별 승차 인원을 비교해줘",
    "가장 승차 인원이 많은 정류장은?",
    "출근 1호 노선의 정류장별 인원을 막대그래프로 보여줘",
]
```

### 통근수당 데이터 분석
```python
questions = [
    "노선별 지급수당을 비교해줘",
    "운행거리와 지급수당의 관계를 분석해줘",
    "야간수당이 가장 높은 노선은?",
]
```

## 생성된 차트 확인

차트는 `generated_charts/` 디렉토리에 저장됩니다:

```
generated_charts/
├── chart_20250102_143052.png
├── chart_20250102_143125.png
└── chart_20250102_143201.png
```

파일명 형식: `chart_YYYYMMDD_HHMMSS.png`

## 필요한 라이브러리

```bash
pip install pandas matplotlib seaborn
```

또는

```bash
pip install -r requirements.txt
```

## 트러블슈팅

### 1. 한글 폰트 깨짐
**증상**: 차트의 한글이 깨져서 표시됨

**해결**:
```python
# macOS
plt.rcParams['font.family'] = 'AppleGothic'

# Windows
plt.rcParams['font.family'] = 'Malgun Gothic'

# Linux
plt.rcParams['font.family'] = 'NanumGothic'
```

### 2. 데이터를 찾을 수 없음
**증상**: "데이터를 찾을 수 없습니다"

**원인**: 
- 지식베이스에 관련 데이터 없음
- 검색 쿼리가 너무 구체적

**해결**:
- 더 일반적인 질문으로 변경
- 검색어 확인

### 3. 차트 타입 결정 실패
**증상**: "차트 타입 결정 중 오류 발생"

**원인**:
- LLM API 호출 실패
- 데이터 구조가 예상과 다름

**해결**:
- API 키 확인 (.env 파일)
- 데이터 구조 확인

## 확장 가능성

### 새로운 차트 타입 추가

1. `ChartTypeSchema`에 타입 추가
```python
chart_type: Literal["bar", "line", "pie", "scatter", "heatmap", "table", "새타입"]
```

2. `_create_chart()`에 로직 추가
```python
elif chart_type == "새타입":
    # 새로운 차트 그리기 로직
    pass
```

3. `_decide_chart_type()`의 프롬프트 업데이트
```python
prompt = f"""
...
- 새타입: 사용 사례 설명
...
"""
```

### 새로운 집계 방법 추가

1. `ChartTypeSchema`에 방법 추가
```python
aggregation: Literal["sum", "count", "average", "min", "max", "새방법"]
```

2. `_aggregate_data()`에 로직 추가
```python
elif aggregation == "새방법":
    return df.groupby(x_axis)[y_axis].새방법().reset_index()
```

## 참고 자료

- [LangGraph 문서](https://langchain-ai.github.io/langgraph/)
- [Pandas 문서](https://pandas.pydata.org/docs/)
- [Matplotlib 문서](https://matplotlib.org/stable/contents.html)
- [Seaborn 문서](https://seaborn.pydata.org/)
