"""
Streamlit Dashboard for Adaptive AI Model Router

Real-time monitoring dashboard showing:
- Live routing decisions table
- Query type distribution chart
- Model usage breakdown
- Latency metrics
- Cache hit rate
"""

import streamlit as st
import requests
import pandas as pd
import time

API_URL = "http://localhost:8000"

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


# ── Sidebar ─────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("🧠 AI Model Router")
    st.markdown("---")

    # Health check
    try:
        health = requests.get(f"{API_URL}/health", timeout=3).json()
        st.success(f"Status: {health['status']}")
        st.markdown("**Active Stages:**")
        for stage in health.get("stages_active", []):
            st.markdown(f"  ✅ `{stage}`")
        st.markdown("**Providers:**")
        for p in health.get("available_providers", []):
            st.markdown(f"  🔗 `{p}`")
    except Exception:
        st.error("⚠️ API not reachable")

    st.markdown("---")

    # Interactive query tester
    st.subheader("🔬 Test a Query")
    test_query = st.text_area("Query", "What is quantum computing?", height=80)
    test_mode = st.selectbox("Mode", ["speed", "cost", "quality"])

    if st.button("🚀 Route Query", use_container_width=True):
        with st.spinner("Routing..."):
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
                    st.markdown(f"**Type:** `{resp['query_type']}`")
                    st.markdown(f"**Model:** `{resp['model_used']}`")
                    st.markdown(f"**Provider:** `{resp['provider']}`")
                    st.markdown(f"**Cache Hit:** `{resp['cache_hit']}`")
                    st.markdown(f"**Latency:** `{resp['latency_ms']:.0f}ms`")
                    st.markdown(f"**Confidence:** `{resp['confidence']:.0%}`")
                    with st.expander("Full Response"):
                        st.write(resp['response'])
            except Exception as e:
                st.error(f"Request failed: {e}")

    st.markdown("---")
    auto_refresh = st.checkbox("🔄 Auto-refresh (5s)", value=False)


# ── Main Dashboard ──────────────────────────────────────────────────────

st.title("📊 Routing Dashboard")

# Fetch logs
try:
    logs_data = requests.get(f"{API_URL}/logs?limit=100", timeout=5).json()
    logs = logs_data.get("logs", [])
except Exception:
    logs = []
    st.warning("Could not fetch logs from API")

if not logs:
    st.info("No routing decisions yet. Use the sidebar to send your first query! 👈")
    st.stop()

df = pd.DataFrame(logs)

# ── Metrics Row ─────────────────────────────────────────────────────────

col1, col2, col3, col4, col5, col6 = st.columns(6)

total_queries = len(df)
avg_latency = df["latency_ms"].mean()
cache_hits = df["cache_hit"].sum()
cache_rate = (cache_hits / total_queries * 100) if total_queries > 0 else 0
unique_models = df["model_used"].nunique()
avg_confidence = df["confidence"].mean()

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
display_df = df[["id", "timestamp", "query_preview", "query_type", "mode", "model_used", "latency_ms", "cache_hit", "confidence"]].copy()
display_df.columns = ["#", "Timestamp", "Query", "Type", "Mode", "Model", "Latency (ms)", "Cache Hit", "Confidence"]

# Color code cache hits
st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Latency (ms)": st.column_config.NumberColumn(format="%.0f ms"),
        "Confidence": st.column_config.NumberColumn(format="%.0f%%"),
        "Cache Hit": st.column_config.CheckboxColumn(),
    },
)

# ── Auto-refresh ────────────────────────────────────────────────────────

if auto_refresh:
    time.sleep(5)
    st.rerun()
