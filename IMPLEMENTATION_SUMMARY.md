# 데이터 분석 및 차트 생성 기능 추가 완료 ✅

## 추가된 파일

### 1. `test_analysis.py` (새 파일)
- 분석 기능 테스트 스크립트
- 다양한 분석 질문으로 에이전트 테스트

### 2. `ANALYSIS_GUIDE.md` (새 파일)
- 상세한 사용 가이드
- 아키텍처 설명
- 트러블슈팅 가이드
- 확장 방법

## 수정된 파일

### 1. `requirements.txt`
**추가된 라이브러리:**
```txt
pandas>=2.0.0          # 데이터 분석
matplotlib>=3.7.0      # 차트 생성
seaborn>=0.12.0        # 고급 시각화
```

### 2. `cs_agent/tools.py`
**추가된 임포트:**
- pandas, matplotlib, seaborn
- Pydantic BaseModel, Field
- os (파일 관리용)

**추가된 클래스:**
- `ChartTypeSchema`: LLM이 차트 타입을 결정하기 위한 Pydantic 스키마

**추가된 함수:**
1. `_extract_structured_data()`
   - 검색 결과에서 JSON 파싱
   - 구조화된 데이터 추출

2. `_decide_chart_type()`
   - LLM을 사용해 차트 타입 결정
   - DataFrame 컬럼 정보 분석
   - Structured Output 사용

3. `_aggregate_data()`
   - pandas groupby로 데이터 집계
   - sum, count, average, min, max 지원

4. `_create_chart()`
   - matplotlib/seaborn으로 차트 생성
   - bar, line, pie, scatter, heatmap 지원
   - 한글 폰트 설정
   - PNG 파일로 저장

5. `analyze_and_visualize` (Tool)
   - 전체 분석 파이프라인 orchestration
   - 7단계 처리 과정:
     1. 지식베이스 검색
     2. 구조화된 데이터 추출
     3. DataFrame 변환
     4. LLM이 차트 타입 결정
     5. 데이터 집계
     6. 차트 생성
     7. 결과 메시지 반환

### 3. `cs_agent/agents/react_agent.py`
**변경 사항:**
- `analyze_and_visualize` 도구 추가
- 시스템 프롬프트 업데이트 (분석 기능 설명 추가)
- 전체 파일에 라인별 한글 주석 추가

### 4. `README.md`
**추가된 섹션:**
- "4) Data Analysis & Visualization" 섹션
- 사용 예제
- 차트 저장 위치
- ANALYSIS_GUIDE.md 링크
- "5) Testing" 섹션

### 5. `.gitignore`
**추가된 항목:**
```
generated_charts/     # 생성된 차트 디렉토리
*.png                 # PNG 파일
*.jpg                 # JPG 파일
*.jpeg                # JPEG 파일
```

## 주요 기능

### 1. 자동 차트 타입 선택
LLM이 질문 의도와 데이터 구조를 분석하여 최적의 차트 선택:
- **bar**: 카테고리별 비교
- **line**: 시간별 추세
- **pie**: 비율 분석
- **scatter**: 상관관계
- **heatmap**: 2차원 패턴
- **table**: 정확한 수치

### 2. 자동 데이터 집계
- sum (합계)
- count (개수)
- average (평균)
- min (최소값)
- max (최대값)

### 3. 한글 지원
- 한글 폰트 설정 (AppleGothic)
- 한글 레이블 정상 표시
- 마이너스 기호 깨짐 방지

## 사용 방법

### CLI에서 사용
```bash
# 막대 그래프 (카테고리 비교)
python cli.py react --question "노선별 승차 인원을 비교해줘"

# 선 그래프 (시간별 추세)
python cli.py react --question "출발시간대별 통근수당 추이를 보여줘"

# 파이 차트 (비율)
python cli.py react --question "각 노선의 운행거리 비율을 파이 차트로 보여줘"
```

### 테스트 실행
```bash
python test_analysis.py
```

## 처리 흐름

```
사용자 질문
    ↓
search_knowledge_base (도구 호출)
    ↓ 
JSON 데이터 검색
    ↓
analyze_and_visualize (도구 호출)
    ↓
1. JSON → 구조화된 데이터 추출
2. DataFrame 변환
3. LLM이 차트 타입 결정 (Structured Output)
4. 데이터 집계 (pandas groupby)
5. 차트 생성 (matplotlib/seaborn)
6. PNG 파일 저장 (generated_charts/)
    ↓
결과 메시지 반환
```

## 필요한 설치

```bash
pip install pandas matplotlib seaborn
```

또는

```bash
pip install -r requirements.txt
```

## 생성되는 파일

```
generated_charts/
├── chart_20250102_143052.png
├── chart_20250102_143125.png
└── chart_20250102_143201.png
```

## 코드 품질

✅ 모든 추가/수정 코드에 라인별 한글 주석 작성
✅ Docstring 추가 (함수/클래스 설명)
✅ 타입 힌팅 사용
✅ 에러 핸들링 포함
✅ 사용자 친화적 메시지
✅ matplotlib 백엔드 설정 (메인 스레드 오류 방지)

## 중요 수정 사항

### matplotlib 백엔드 설정
멀티스레드 환경에서 GUI 오류를 방지하기 위해 non-interactive 백엔드 사용:
```python
import matplotlib
matplotlib.use('Agg')  # GUI 없이 파일만 저장
import matplotlib.pyplot as plt
```

이 설정으로:
- ✅ 메인 스레드 오류 방지
- ✅ 백그라운드에서 차트 생성 가능
- ✅ CLI 환경에서 안정적 동작

## 다음 단계

1. **라이브러리 설치**
   ```bash
   pip install pandas matplotlib seaborn
   ```

2. **테스트 실행**
   ```bash
   python test_analysis.py
   ```

3. **실제 사용**
   ```bash
   python cli.py react --question "노선별 승차 인원 비교해줘"
   ```

4. **생성된 차트 확인**
   ```bash
   open generated_charts/chart_*.png
   ```

## 참고 문서

- [ANALYSIS_GUIDE.md](./ANALYSIS_GUIDE.md): 상세 가이드
- [test_analysis.py](./test_analysis.py): 테스트 예제
- [README.md](./README.md): 프로젝트 개요

## 테스트 결과 ✅

### 테스트 1: 노선별 승차 인원 비교
```bash
python cli.py react --question "노선별 승차 인원 비교해줘"
```

**결과:**
- ✅ 성공적으로 막대 그래프 생성
- ✅ 차트 저장: `generated_charts/chart_20251002_063600.png`
- ✅ 5개 노선의 승차 인원 데이터 시각화
- ✅ 한글 레이블 정상 표시

### 테스트 2: 노선별 지급수당 비교
```bash
python cli.py react --question "노선별 지급수당을 비교해서 보여줘"
```

**결과:**
- ✅ 성공적으로 막대 그래프 생성
- ✅ 차트 저장: `generated_charts/chart_20251002_063750.png`
- ✅ 운행단가 데이터 시각화
- ✅ 모든 기능 정상 작동

## 확장 가능성

새로운 차트 타입이나 집계 방법을 추가하려면:
1. `ChartTypeSchema`에 타입 추가
2. `_create_chart()`에 그리기 로직 추가
3. `_decide_chart_type()` 프롬프트 업데이트

자세한 내용은 ANALYSIS_GUIDE.md의 "확장 가능성" 섹션 참고
