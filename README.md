# 🧠 Adaptive AI Model Router

> Intelligent LLM routing service that classifies queries and routes them to the optimal model based on **Speed / Cost / Quality** mode selection.

**Built for the AI Infra Summit Hackathon 2026**

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green)
![LangGraph](https://img.shields.io/badge/LangGraph-Decision_Graph-purple)
![Groq](https://img.shields.io/badge/Groq-Inference-orange)

---

## 🎯 What It Does

Instead of hardcoding which LLM to use, the **Adaptive AI Model Router** dynamically selects the best model for each query:

1. **Classifies** the query type (factual / reasoning / creative / code) using an LLM
2. **Routes** to the optimal model based on user-selected mode (Speed / Cost / Quality)
3. **Caches** semantically similar queries in Qdrant to avoid redundant LLM calls
4. **Logs** every decision to PostgreSQL for analytics
5. **Visualizes** routing patterns on a real-time Streamlit dashboard

### Routing Decision Graph (LangGraph)

```
START → classify → select_model → check_cache
    → (cache hit)  → log_decision → END
    → (cache miss) → call_llm → store_cache → log_decision → END
```

---

## 🏗️ Architecture

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **API** | FastAPI | REST endpoints for routing, health, logs |
| **Decision Graph** | LangGraph | Stateful routing pipeline with conditional edges |
| **Classification** | Groq LLM + keyword fallback | Query type detection with confidence scores |
| **LLM Providers** | Groq (primary), OpenAI/Gemini (fallback) | Multi-provider inference |
| **Semantic Cache** | Qdrant + FastEmbed | Deduplicate similar queries |
| **Decision Logging** | PostgreSQL + SQLAlchemy | Full audit trail |
| **Dashboard** | Streamlit | Real-time monitoring & interactive testing |

### Routing Matrix

| Query Type \ Mode | ⚡ Speed | 💰 Cost | 🏆 Quality |
|---|---|---|---|
| **Factual** | compound-mini | allam-2-7b | gpt-oss-120b |
| **Reasoning** | qwen3.8-27b | allam-2-7b | gpt-oss-120b |
| **Creative** | compound-mini | allam-2-7b | gpt-oss-120b |
| **Code** | qwen3.8-27b | allam-2-7b | gpt-oss-120b |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- Groq API key ([get one free](https://console.groq.com))

### 1. Clone & Setup
```bash
git clone <repo-url>
cd adaptive-ai-router
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure
```bash
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```

### 3. Start Infrastructure
```bash
docker compose up -d  # PostgreSQL + Qdrant
```

### 4. Run the API
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Launch Dashboard
```bash
streamlit run dashboard.py
```

### 6. Try It!
```bash
# Speed mode — fast factual answer
curl -X POST http://localhost:8000/route \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the capital of France?", "mode": "speed"}'

# Quality mode — detailed reasoning
curl -X POST http://localhost:8000/route \
  -H "Content-Type: application/json" \
  -d '{"query": "Explain quantum entanglement step by step", "mode": "quality"}'

# Cost mode — cheapest model
curl -X POST http://localhost:8000/route \
  -H "Content-Type: application/json" \
  -d '{"query": "Write a Python quicksort", "mode": "cost"}'
```

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | System health, active stages, available providers |
| `POST` | `/route` | Route a query → classify + select model + LLM call |
| `GET` | `/logs` | Recent routing decisions (for dashboard) |
| `GET` | `/models` | Full routing matrix |
| `GET` | `/docs` | Interactive Swagger UI |

---

## 📂 Project Structure

```
adaptive-ai-router/
├── app/
│   ├── main.py           # FastAPI app + endpoints
│   ├── config.py          # Settings from .env
│   ├── models.py          # Pydantic request/response schemas
│   ├── classifier.py      # LLM + keyword query classifier
│   ├── providers.py       # Routing matrix + multi-LLM dispatch
│   ├── router_graph.py    # LangGraph decision graph
│   ├── database.py        # PostgreSQL logging (SQLAlchemy)
│   └── cache.py           # Qdrant semantic cache
├── dashboard.py           # Streamlit monitoring dashboard
├── docker-compose.yml     # PostgreSQL + Qdrant
├── requirements.txt
├── .env
└── README.md
```

---

## 🔑 Key Features

- **LLM-powered classification** with keyword fallback (99% confidence on tested queries)
- **Conditional graph routing** — cache hits skip the LLM call entirely
- **Semantic deduplication** — similar queries return cached responses instantly
- **Graceful degradation** — every infrastructure component (DB, cache) fails silently
- **Full audit trail** — every routing decision logged with metadata
- **Real-time dashboard** — interactive query tester + metrics + charts

---

## 📄 License

MIT — built with ❤️ for the AI Infra Summit Hackathon 2026
