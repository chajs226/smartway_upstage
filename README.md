## Customer Support Agent (LangGraph)

This project mirrors the `Customer_Support_Agent.ipynb` notebook as a runnable Python package using LangGraph, LangChain, Upstage Solar, FAISS, and Tavily web search.

### 1) Setup

- Python 3.10+
- macOS (darwin 24 tested)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env with your keys
```

- Required env vars in `.env`:
  - `UPSTAGE_API_KEY`
  - `TAVILY_API_KEY`

### 2) Project layout

```
smartway_upstage/
  cs_agent/
    __init__.py
    config.py
    data.py
    embeddings.py
    tools.py
    agents/
      react_agent.py
    workflows/
      customer_support.py
  cli.py
  requirements.txt
  .env.example
  README.md
  Customer_Support_Agent.ipynb
```

### 3) Quick start

- Simple ReAct agent (prebuilt):
```bash
python cli.py react --question "우리 회사 API에 접속이 잘 안되는데."
```

- Full workflow (custom graph with interrupts):
```bash
python cli.py workflow
# It will ask for Customer ID (e.g., CUST001) and then your question
```

### 4) Data Analysis & Visualization 🆕

**New Feature**: Automatic chart generation based on user questions!

The agent can now:
- Analyze data from knowledge base (승하차정보.json, 통근수당.json)
- Automatically select appropriate chart types (bar, line, pie, scatter, heatmap)
- Aggregate data intelligently (sum, count, average, min, max)
- Generate and save visualizations

Example questions:
```bash
# Compare boarding numbers by route
python cli.py react --question "노선별 승차 인원을 비교해줘"

# Show trend of commute allowance
python cli.py react --question "출발시간대별 통근수당 추이를 보여줘"

# Analyze proportions
python cli.py react --question "각 노선의 운행거리 비율을 파이 차트로 보여줘"
```

Charts are saved in: `generated_charts/chart_YYYYMMDD_HHMMSS.png`

For detailed guide, see [ANALYSIS_GUIDE.md](./ANALYSIS_GUIDE.md)

### 5) Testing

Run analysis tests:
```bash
python test_analysis.py
```

### 6) Notes
- The code uses the Upstage OpenAI-compatible API and Tavily Client.
- FAISS is used to index in-memory knowledge base documents as in the notebook.
- The workflow reproduces the state, tools, conditional edges, and escalation logic shown in the notebook.
- **New**: `analyze_and_visualize` tool uses LLM to determine optimal chart types and creates visualizations automatically.
