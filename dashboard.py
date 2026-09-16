"""
Streamlit Dashboard for Adaptive AI Model Router

Real-time monitoring dashboard showing:
- Live routing decisions table
- Query type distribution chart
- Model usage breakdown
- Latency metrics
- Cache hit rate

Supports both connected mode (via FastAPI) and standalone cloud mode (Streamlit Community Cloud).
"""

import os
import time
import asyncio
import pandas as pd
import requests
import streamlit as st

# Check for API URL from environment or fallback to localhost
API_URL = os.getenv("API_URL", "http://localhost:8000")

# Check for Groq API Key from Streamlit Secrets or Environment
if "GROQ_API_KEY" in st.secrets:
    os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]

st.set_page_config(
    page_title="AI Model Router Dashboard",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ──────────────────────────────────────────────────────────

st.markdown("""
<style>
    .stMetric { background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); border-radius: 12px; padding: 16px; border: 1px solid #0f3460; }
    .stMetric label { color: #a3bffa !important; font-size: 0.85rem; }
    .stMetric [data-testid="stMetricValue"] { color: #e2e8f0 !important; font-size: 2rem; }
    div[data-testid="stHorizontalBlock"] > div { padding: 0 4px; }
    .route-btn { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; border-radius: 8px; padding: 12px 24px; font-size: 1rem; cursor: pointer; }
</style>
""", unsafe_allow_html=True)

# ── Session State for In-Memory Logs (Cloud Fallback) ───────────────────

if "in_memory_logs" not in st.session_state:
    st.session_state["in_memory_logs"] = []

# ── Sidebar ─────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("🧠 AI Model Router")
    st.markdown("---")

    # Check API health
    api_connected = False
    try:
        health = requests.get(f"{API_URL}/health", timeout=2).json()
        api_connected = True
        st.success(f"API Mode: Connected ({API_URL})")
        st.markdown("**Active Stages:**")
        for stage in health.get("stages_active", []):
            st.markdown(f"  ✅ `{stage}`")
        st.markdown("**Providers:**")
        for p in health.get("available_providers", []):
            st.markdown(f"  🔗 `{p}`")
    except Exception:
        api_connected = False
        st.info("☁️ **Cloud Standalone Mode** (Direct In-Process Engine)")
        
        # Optional API Key input if not in env
        if not os.getenv("GROQ_API_KEY"):
            custom_key = st.text_input("Enter Groq API Key", type="password")
            if custom_key:
                os.environ["GROQ_API_KEY"] = custom_key
                st.success("API key loaded!")
        else:
            st.caption("✓ Groq API Key configured")

    st.markdown("---")

    # Interactive query tester
    st.subheader("🔬 Test a Query")
    test_query = st.text_area("Query", "What is quantum computing?", height=80)
    test_mode = st.selectbox("Mode", ["speed", "cost", "quality"])

    if st.button("🚀 Route Query", use_container_width=True):
        with st.spinner("Routing query through decision graph..."):
            if api_connected:
                # Route through FastAPI endpoint
                try:
                    resp = requests.post(
                        f"{API_URL}/route",
                        json={"query": test_query, "mode": test_mode},
                        timeout=30,
                    ).json()

                    if "detail" in resp:
                        st.error(f"Error: {resp['detail']}")
                    else:
                        st.success("Routed successfully!")
                        st.markdown(f"**Type:** `{resp.get('query_type')}`")
                        st.markdown(f"**Model:** `{resp.get('model_used') or resp.get('selected_model')}`")
                        st.markdown(f"**Provider:** `{resp.get('provider', 'groq')}`")
                        st.markdown(f"**Cache Hit:** `{resp.get('cache_hit') or resp.get('cached')}`")
                        st.markdown(f"**Latency:** `{resp.get('latency_ms', 0):.0f}ms`")
                        st.markdown(f"**Confidence:** `{resp.get('confidence', 0.99):.0%}`")
                        with st.expander("Full Response"):
                            st.write(resp.get('response', ''))
                except Exception as e:
                    st.error(f"Request failed: {e}")
            else:
                # Standalone in-process routing using LangGraph directly
                try:
                    from app.router_graph import router_graph

                    t0 = time.time()
                    initial_state = {
                        "query": test_query,
                        "mode": test_mode,
                        "query_type": "",
                        "classification_confidence": 0.0,
                        "classification_reasoning": "",
                        "classification_method": "llm",
                        "provider": "",
                        "model": "",
                        "routing_reasoning": "",
                        "response": "",
                        "latency_ms": 0.0,
                        "cache_hit": False,
                        "log_id": None,
                        "error": None,
                    }

                    result = asyncio.run(router_graph.ainvoke(initial_state))
                    total_time = (time.time() - t0) * 1000

                    st.success("Routed successfully in-process!")
                    st.markdown(f"**Type:** `{result.get('query_type')}`")
                    st.markdown(f"**Model:** `{result.get('model')}`")
                    st.markdown(f"**Provider:** `{result.get('provider')}`")
                    st.markdown(f"**Cache Hit:** `{result.get('cache_hit')}`")
                    st.markdown(f"**Latency:** `{total_time:.0f}ms`")
                    st.markdown(f"**Confidence:** `{result.get('classification_confidence', 0.99):.0%}`")
                    with st.expander("Full Response"):
                        st.write(result.get('response', ''))

                    # Store in session state for instant dashboard charting
                    log_entry = {
                        "id": len(st.session_state["in_memory_logs"]) + 1,
                        "timestamp": pd.Timestamp.now().isoformat(),
                        "query_preview": test_query[:50] + "..." if len(test_query) > 50 else test_query,
                        "query_type": result.get("query_type"),
                        "mode": test_mode,
                        "provider": result.get("provider"),
                        "model_used": result.get("model"),
                        "latency_ms": total_time,
                        "cache_hit": result.get("cache_hit", False),
                        "confidence": result.get("classification_confidence", 0.99),
                    }
                    st.session_state["in_memory_logs"].insert(0, log_entry)

                except Exception as e:
                    st.error(f"In-process routing error: {e}")

    st.markdown("---")
    auto_refresh = st.checkbox("🔄 Auto-refresh (5s)", value=False)


# ── Main Dashboard ──────────────────────────────────────────────────────

st.title("📊 Routing Dashboard")

# Fetch logs from API or in-memory
logs = []
if api_connected:
    try:
        logs_data = requests.get(f"{API_URL}/logs?limit=100", timeout=5).json()
        logs = logs_data.get("logs", [])
    except Exception:
        logs = st.session_state.get("in_memory_logs", [])
else:
    logs = st.session_state.get("in_memory_logs", [])

if not logs:
    st.info("No routing decisions yet. Use the sidebar on the left to send your first query! 👈")
    st.stop()

df = pd.DataFrame(logs)

# ── Metrics Row ─────────────────────────────────────────────────────────

col1, col2, col3, col4, col5, col6 = st.columns(6)

total_queries = len(df)
avg_latency = df["latency_ms"].mean()
cache_hits = df["cache_hit"].sum()
cache_rate = (cache_hits / total_queries * 100) if total_queries > 0 else 0
unique_models = df["model_used"].nunique()
avg_confidence = df["confidence"].mean() if "confidence" in df.columns else 0.99

col1.metric("Total Queries", total_queries)
col2.metric("Avg Latency", f"{avg_latency:.0f}ms")
col3.metric("Cache Hits", int(cache_hits))
col4.metric("Cache Hit Rate", f"{cache_rate:.0f}%")
col5.metric("Models Used", unique_models)
col6.metric("Avg Confidence", f"{avg_confidence:.0%}")

st.markdown("---")

# ── Charts Row ──────────────────────────────────────────────────────────

chart_col1, chart_col2, chart_col3 = st.columns(3)

with chart_col1:
    st.subheader("📋 Query Types")
    type_counts = df["query_type"].value_counts()
    st.bar_chart(type_counts)

with chart_col2:
    st.subheader("🤖 Models Used")
    model_counts = df["model_used"].value_counts()
    st.bar_chart(model_counts)

with chart_col3:
    st.subheader("⚡ Mode Distribution")
    mode_counts = df["mode"].value_counts()
    st.bar_chart(mode_counts)

st.markdown("---")

# ── Latency Over Time ──────────────────────────────────────────────────

st.subheader("📈 Latency Over Time")
if "timestamp" in df.columns:
    df_time = df.copy()
    df_time["timestamp"] = pd.to_datetime(df_time["timestamp"])
    df_time = df_time.sort_values("timestamp")
    st.line_chart(df_time.set_index("timestamp")["latency_ms"])

st.markdown("---")

# ── Recent Decisions Table ──────────────────────────────────────────────

st.subheader("📜 Recent Routing Decisions")
cols_to_display = ["id", "timestamp", "query_preview", "query_type", "mode", "model_used", "latency_ms", "cache_hit", "confidence"]
valid_cols = [c for c in cols_to_display if c in df.columns]
display_df = df[valid_cols].copy()

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "latency_ms": st.column_config.NumberColumn("Latency (ms)", format="%.0f ms"),
        "confidence": st.column_config.NumberColumn("Confidence", format="%.0%"),
        "cache_hit": st.column_config.CheckboxColumn("Cache Hit"),
    },
)

# ── Auto-refresh ────────────────────────────────────────────────────────

if auto_refresh:
    time.sleep(5)
    st.rerun()
