import os
import json
import time
import tempfile
import streamlit as st
import pandas as pd
import plotly.express as px

from src.engine import StructuralDiscoveryEngine
from src.ingestion import CloudDataIngestor
from src.db_manager import DatabaseManager
from src.ai_layer import AIHybridAnalyticsLayer
from src.analytics import FinOpsAnalyticsEngine
from src.notifier import AlertNotifier
from src.reporter import BrutalMatrixReporter

# 1. Page Configuration
st.set_page_config(
    page_title="Hybrid AI Cloud Command Center",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Custom theme and interaction styling
st.markdown("""
<style>
    :root {
        --canvas: #080d18;
        --surface: rgba(17, 26, 44, 0.78);
        --surface-raised: rgba(24, 36, 59, 0.88);
        --line: rgba(148, 163, 184, 0.16);
        --muted: #94a3b8;
        --text: #e7eefb;
        --cyan: #38bdf8;
        --violet: #8b7cff;
        --green: #34d399;
        --red: #fb7185;
        --ease: cubic-bezier(0.22, 1, 0.36, 1);
    }

    @keyframes enter {
        from { opacity: 0; transform: translateY(12px); }
        to { opacity: 1; transform: translateY(0); }
    }

    @keyframes glow {
        0%, 100% { box-shadow: 0 0 0 0 rgba(251, 113, 133, 0); }
        50% { box-shadow: 0 0 0 5px rgba(251, 113, 133, 0.12); }
    }

    @keyframes statusPulse {
        0%, 100% { opacity: 1; box-shadow: 0 0 0 0 rgba(52, 211, 153, 0.4); }
        50% { opacity: 0.72; box-shadow: 0 0 0 5px rgba(52, 211, 153, 0); }
    }

    .stApp {
        color: var(--text);
        background:
            radial-gradient(ellipse at 12% 0%, rgba(56, 189, 248, 0.09), transparent 34rem),
            radial-gradient(ellipse at 92% 8%, rgba(139, 124, 255, 0.10), transparent 32rem),
            var(--canvas);
    }

    [data-testid="stHeader"] {
        background: rgba(8, 13, 24, 0.72);
        backdrop-filter: blur(16px);
    }

    [data-testid="stMainBlockContainer"] {
        max-width: 1500px;
        padding-top: 2rem;
        padding-bottom: 4rem;
    }

    .hero-banner {
        position: relative;
        isolation: isolate;
        overflow: hidden;
        background:
            radial-gradient(ellipse at 84% 0%, rgba(139, 124, 255, 0.22), transparent 27rem),
            linear-gradient(125deg, rgba(15, 27, 47, 0.98), rgba(15, 19, 42, 0.96) 58%, rgba(22, 20, 52, 0.98));
        border: 1px solid rgba(125, 151, 196, 0.22);
        border-radius: 24px;
        padding: clamp(24px, 4vw, 42px);
        margin: 0 0 28px;
        box-shadow: 0 24px 70px rgba(0, 0, 0, 0.28), inset 0 1px 0 rgba(255, 255, 255, 0.06);
        animation: enter 700ms var(--ease) both;
        transition: border-color 350ms ease, box-shadow 350ms ease, transform 350ms var(--ease);
    }

    .hero-banner::after {
        position: absolute;
        z-index: -1;
        top: -110px;
        right: 8%;
        width: 290px;
        height: 290px;
        border: 1px solid rgba(125, 151, 196, 0.12);
        border-radius: 50%;
        box-shadow: 0 0 0 35px rgba(125, 151, 196, 0.035), 0 0 0 70px rgba(125, 151, 196, 0.025);
        content: "";
        transition: transform 700ms var(--ease);
    }

    .hero-banner:hover {
        border-color: rgba(56, 189, 248, 0.36);
        box-shadow: 0 28px 80px rgba(0, 0, 0, 0.34), 0 0 40px rgba(56, 189, 248, 0.06);
        transform: translateY(-2px);
    }

    .hero-banner:hover::after {
        transform: scale(1.08) translate(-8px, 6px);
    }

    .hero-content {
        display: flex;
        position: relative;
        z-index: 1;
        align-items: flex-start;
        justify-content: space-between;
        gap: 24px;
    }

    .hero-copy {
        max-width: 900px;
    }

    .hero-eyebrow {
        margin: 0 0 10px;
        color: #7dd3fc;
        font-size: 0.72rem;
        font-weight: 800;
        letter-spacing: 0.2em;
        text-transform: uppercase;
    }

    .hero-title {
        margin: 0;
        color: var(--text);
        font-size: clamp(1.8rem, 3.3vw, 2.8rem);
        font-weight: 800;
        letter-spacing: -0.045em;
        line-height: 1.12;
        background: linear-gradient(100deg, #e0f2fe 5%, #7dd3fc 42%, #c4b5fd 88%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .hero-subtitle {
        max-width: 690px;
        margin: 14px 0 0;
        color: #a7b5ca;
        font-size: 0.98rem;
        line-height: 1.7;
    }

    .hero-subtitle b {
        color: #dce8f8;
        font-weight: 650;
    }

    .hero-status {
        display: inline-flex;
        align-items: center;
        gap: 10px;
        flex: 0 0 auto;
        margin-top: 4px;
        padding: 10px 14px;
        border: 1px solid rgba(52, 211, 153, 0.24);
        border-radius: 999px;
        background: rgba(16, 185, 129, 0.08);
        color: #a7f3d0;
        font-size: 0.72rem;
        font-weight: 750;
        letter-spacing: 0.11em;
        white-space: nowrap;
    }

    .hero-status::before {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: var(--green);
        animation: statusPulse 2.4s ease-in-out infinite;
        content: "";
    }

    [data-testid="stSidebar"] {
        border-right: 1px solid var(--line);
        background: linear-gradient(180deg, rgba(13, 21, 36, 0.98), rgba(9, 15, 27, 0.98));
    }

    [data-testid="stSidebar"] > div:first-child {
        background: transparent;
    }

    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h2 {
        padding-bottom: 12px;
        border-bottom: 1px solid var(--line);
        color: #e2e8f0;
        font-size: 1.08rem;
        letter-spacing: -0.02em;
    }

    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
        color: #bdc9dc;
        font-size: 0.84rem;
        font-weight: 600;
    }

    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"] {
        animation: enter 500ms var(--ease) both;
    }

    div[data-testid="metric-container"] {
        min-height: 122px;
        padding: 20px 21px;
        border: 1px solid var(--line);
        border-radius: 18px;
        background: linear-gradient(145deg, rgba(22, 34, 55, 0.94), rgba(15, 24, 41, 0.92));
        box-shadow: 0 10px 28px rgba(0, 0, 0, 0.14), inset 0 1px 0 rgba(255, 255, 255, 0.035);
        animation: enter 600ms var(--ease) both;
        transition: transform 280ms var(--ease), border-color 280ms ease, box-shadow 280ms ease, background 280ms ease;
    }

    div[data-testid="column"]:nth-child(2) div[data-testid="metric-container"] { animation-delay: 70ms; }
    div[data-testid="column"]:nth-child(3) div[data-testid="metric-container"] { animation-delay: 140ms; }
    div[data-testid="column"]:nth-child(4) div[data-testid="metric-container"] { animation-delay: 210ms; }

    div[data-testid="metric-container"] label {
        color: #a7b5ca !important;
        font-size: 0.78rem !important;
        font-weight: 650 !important;
        letter-spacing: 0.035em;
    }

    div[data-testid="metric-container"]:hover {
        transform: translateY(-5px);
        border-color: rgba(56, 189, 248, 0.42);
        background: linear-gradient(145deg, rgba(27, 43, 69, 0.98), rgba(17, 29, 49, 0.96));
        box-shadow: 0 18px 38px rgba(0, 0, 0, 0.24), 0 0 26px rgba(56, 189, 248, 0.08);
    }

    .badge-critical {
        display: inline-flex;
        align-items: center;
        vertical-align: middle;
        background: rgba(244, 63, 94, 0.10);
        color: #fda4af;
        border: 1px solid rgba(251, 113, 133, 0.34);
        padding: 5px 11px;
        border-radius: 999px;
        font-size: 0.68rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        animation: glow 2.8s ease-in-out infinite;
    }

    .badge-healthy {
        display: inline-flex;
        align-items: center;
        gap: 9px;
        background: rgba(16, 185, 129, 0.08);
        color: #a7f3d0;
        border: 1px solid rgba(52, 211, 153, 0.22);
        padding: 9px 13px;
        border-radius: 999px;
        font-size: 0.7rem;
        font-weight: 750;
        letter-spacing: 0.1em;
        white-space: nowrap;
    }

    .badge-healthy::first-letter {
        color: var(--green);
    }

    div[data-testid="stExpander"] {
        overflow: hidden;
        border: 1px solid var(--line);
        border-radius: 16px;
        background: linear-gradient(145deg, rgba(19, 29, 48, 0.88), rgba(12, 20, 35, 0.9));
        animation: enter 500ms var(--ease) both;
        transition: border-color 250ms ease, box-shadow 250ms ease, transform 250ms var(--ease);
    }

    div[data-testid="stExpander"]:hover {
        transform: translateY(-2px);
        border-color: rgba(139, 124, 255, 0.38);
        box-shadow: 0 12px 28px rgba(0, 0, 0, 0.2);
    }

    div[data-testid="stExpander"] summary {
        padding: 0.8rem 1rem;
        transition: background 200ms ease, color 200ms ease;
    }

    div[data-testid="stExpander"] summary:hover {
        background: rgba(139, 124, 255, 0.055);
    }

    [data-testid="stTabs"] {
        margin-top: 8px;
    }

    [data-testid="stTabs"] [role="tablist"] {
        gap: 8px;
        border-bottom: 1px solid var(--line);
    }

    [data-testid="stTabs"] button[role="tab"] {
        min-height: 46px;
        padding: 0 16px;
        border: 1px solid transparent;
        border-radius: 12px 12px 0 0;
        color: #9eacc2;
        font-size: 0.86rem;
        font-weight: 650;
        transition: color 200ms ease, background 200ms ease, border-color 200ms ease, transform 200ms var(--ease);
    }

    [data-testid="stTabs"] button[role="tab"]:hover {
        transform: translateY(-2px);
        border-color: rgba(148, 163, 184, 0.12);
        background: rgba(148, 163, 184, 0.06);
        color: #e2e8f0;
    }

    [data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
        border-color: rgba(56, 189, 248, 0.22);
        background: linear-gradient(180deg, rgba(56, 189, 248, 0.12), rgba(56, 189, 248, 0.035));
        color: #bae6fd;
    }

    [data-testid="stTabs"] [data-testid="stTabContent"] {
        padding-top: 22px;
        animation: enter 420ms var(--ease) both;
    }

    div.stButton > button[kind="primary"] {
        min-height: 48px;
        border: 1px solid rgba(125, 211, 252, 0.28);
        border-radius: 13px;
        background: linear-gradient(105deg, #087eae, #6254d9 58%, #8050c9);
        color: white;
        font-weight: 750;
        letter-spacing: 0.015em;
        box-shadow: 0 8px 22px rgba(79, 70, 229, 0.2), inset 0 1px 0 rgba(255, 255, 255, 0.16);
        transition: transform 220ms var(--ease), box-shadow 220ms ease, filter 220ms ease;
    }

    div.stButton > button[kind="primary"]:hover {
        transform: translateY(-2px);
        filter: brightness(1.12);
        box-shadow: 0 13px 30px rgba(79, 70, 229, 0.34), 0 0 24px rgba(56, 189, 248, 0.12);
    }

    div.stButton > button,
    [data-testid="stDownloadButton"] button {
        border-radius: 11px;
        transition: transform 200ms var(--ease), border-color 200ms ease, background 200ms ease, box-shadow 200ms ease;
    }

    div.stButton > button:not([kind="primary"]):hover,
    [data-testid="stDownloadButton"] button:hover {
        transform: translateY(-1px);
        border-color: rgba(56, 189, 248, 0.4);
        box-shadow: 0 8px 18px rgba(0, 0, 0, 0.14);
    }

    [data-testid="stDataFrame"], [data-testid="stTable"] {
        overflow: hidden;
        border: 1px solid var(--line);
        border-radius: 14px;
        background: rgba(14, 22, 38, 0.72);
        animation: enter 500ms var(--ease) both;
    }

    [data-testid="stPlotlyChart"] {
        overflow: hidden;
        border: 1px solid var(--line);
        border-radius: 18px;
        background: linear-gradient(145deg, rgba(18, 28, 47, 0.88), rgba(11, 18, 32, 0.92));
        box-shadow: 0 12px 32px rgba(0, 0, 0, 0.16);
        animation: enter 550ms var(--ease) both;
        transition: border-color 250ms ease, box-shadow 250ms ease, transform 250ms var(--ease);
    }

    [data-testid="stPlotlyChart"]:hover {
        transform: translateY(-2px);
        border-color: rgba(56, 189, 248, 0.24);
        box-shadow: 0 16px 38px rgba(0, 0, 0, 0.22), 0 0 24px rgba(56, 189, 248, 0.05);
    }

    [data-testid="stAlert"] {
        border-radius: 14px;
        animation: enter 400ms var(--ease) both;
    }

    [data-testid="stStatusWidget"] {
        border: 1px solid var(--line);
        border-radius: 14px;
        background: rgba(17, 26, 44, 0.7);
    }

    [data-testid="stMarkdownContainer"] h2,
    [data-testid="stMarkdownContainer"] h3 {
        color: #e5edf8;
        letter-spacing: -0.025em;
    }

    [data-testid="stMarkdownContainer"] h3 {
        margin-top: 0.5rem;
    }

    [data-testid="stWidgetLabel"] p {
        color: #b7c4d8;
    }

    input, textarea, [data-baseweb="select"] > div {
        border-radius: 10px !important;
    }

    :focus-visible {
        outline: 2px solid rgba(56, 189, 248, 0.85) !important;
        outline-offset: 3px !important;
    }

    ::selection {
        background: rgba(56, 189, 248, 0.3);
        color: white;
    }

    @media (max-width: 760px) {
        [data-testid="stMainBlockContainer"] {
            padding: 1rem 1rem 3rem;
        }

        .hero-content {
            flex-direction: column;
            gap: 18px;
        }

        .hero-banner {
            border-radius: 18px;
        }

        [data-testid="stTabs"] [role="tablist"] {
            gap: 2px;
        }

        [data-testid="stTabs"] button[role="tab"] {
            padding: 0 9px;
            font-size: 0.75rem;
        }
    }

    @media (prefers-reduced-motion: reduce) {
        *, *::before, *::after {
            scroll-behavior: auto !important;
            animation-duration: 0.01ms !important;
            animation-iteration-count: 1 !important;
            transition-duration: 0.01ms !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# 3. Hero Header
st.markdown("""
<div class="hero-banner">
    <div class="hero-content">
        <div class="hero-copy">
            <p class="hero-eyebrow">Cloud intelligence · FinOps · Governance</p>
            <h1 class="hero-title">🛡️ Hybrid AI Cloud Governance & FinOps Command Center</h1>
            <p class="hero-subtitle">Real-Time Anomaly Detection via <b>Isolation Forest ML</b> • <b>Tag Governance</b> • <b>Safe CLI Auto-Remediation</b></p>
        </div>
        <span class="hero-status">SYSTEM ONLINE</span>
    </div>
</div>
""", unsafe_allow_html=True)

# --- SIDEBAR CONTROLS ---
st.sidebar.markdown("## ⚙️ Audit Control Center")
data_mode = st.sidebar.radio(
    "Infrastructure Telemetry Source:",
    ["Simulated Multi-Cloud Fleet (Mock)", "Upload Real Cloud Export (CSV / JSON)"]
)

scale_nodes = 120
uploaded_file = None

if data_mode == "Simulated Multi-Cloud Fleet (Mock)":
    scale_nodes = st.sidebar.slider("Simulated Cloud Fleet Scale", min_value=20, max_value=500, value=160, step=20)
else:
    uploaded_file = st.sidebar.file_uploader("Upload AWS/GCP Inventory (.csv or .json)", type=["csv", "json"])
    st.sidebar.caption(
        "Required data: resource ID, type, cloud provider, region, and monthly cost. "
        "Common header variations are detected automatically."
    )
    if st.sidebar.button("📄 Generate Sample Real CSV"):
        CloudDataIngestor.generate_sample_real_csv("database/sample_cloud_export.csv")
        st.sidebar.success("Created database/sample_cloud_export.csv")

run_audit = st.sidebar.button("🚀 Launch Hybrid Audit Scan", type="primary", use_container_width=True)

if data_mode == "Upload Real Cloud Export (CSV / JSON)" and uploaded_file is None:
    st.info("Upload a cloud inventory CSV or JSON file in the sidebar to run an audit.")
    st.stop()

# --- PIPELINE EXECUTION ---
if run_audit or "evaluated_df" not in st.session_state:
    os.makedirs("database", exist_ok=True)
    db = DatabaseManager()

    with st.status("🔄 Executing Hybrid AI Cloud Audit Pipeline...", expanded=True) as status:
        st.write("📡 **Step 1/4:** Discovering multi-cloud compute, storage, buckets & databases...")
        if data_mode == "Upload Real Cloud Export (CSV / JSON)" and uploaded_file is not None:
            suffix = os.path.splitext(uploaded_file.name)[1]
            tmp_path = None
            ingestion_error = None
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    tmp.write(uploaded_file.getvalue())
                    tmp_path = tmp.name
                inventory = CloudDataIngestor.ingest_from_file(tmp_path)
            except (OSError, ValueError, pd.errors.ParserError) as exc:
                ingestion_error = exc
            finally:
                if tmp_path and os.path.exists(tmp_path):
                    os.remove(tmp_path)

            if ingestion_error:
                st.error(f"Could not process '{uploaded_file.name}': {ingestion_error}")
                st.info(
                    "Check that the file contains cloud inventory rows. Required fields are resource ID, "
                    "resource type, provider, region, and monthly cost. Use the sample CSV as a template."
                )
                st.stop()
            source_label = f"REAL ({uploaded_file.name})"
        else:
            inventory = StructuralDiscoveryEngine.run_discovery_sweep(scale_count=scale_nodes)
            source_label = "MOCK_SIMULATION"
        time.sleep(0.2)

        st.write(f"🗄️ **Step 2/4:** Syncing `{len(inventory)}` normalized nodes into SQLite DBMS...")
        db.clear_stale_records()
        db.pipeline_resource_ingestion(inventory)
        raw_df = db.harvest_analytical_dataframe()
        time.sleep(0.15)

        st.write("🧠 **Step 3/4:** Running Scikit-Learn Isolation Forest & Governance Tag Matrix...")
        evaluated_df = AIHybridAnalyticsLayer.run_hybrid_evaluation(raw_df)
        finops = FinOpsAnalyticsEngine.calculate_executive_metrics(evaluated_df)
        FinOpsAnalyticsEngine.export_cfo_csv_report(finops["waste_dataframe"])
        time.sleep(0.15)

        st.write("🚨 **Step 4/4:** Logging audit snapshot & dispatching critical webhook alerts...")
        sec_count = int((evaluated_df["violation_category"] == "SECURITY_BREACH").sum())
        db.log_audit_run(
            source_label,
            finops["total_resources"],
            finops["total_monthly_spend"],
            finops["wasted_monthly_spend"],
            sec_count
        )
        alerts_sent = AlertNotifier.dispatch_critical_alerts(evaluated_df)

        st.session_state["evaluated_df"] = evaluated_df
        st.session_state["finops"] = finops
        st.session_state["alerts_sent"] = alerts_sent
        st.session_state["history_df"] = db.fetch_historical_runs()

        status.update(label="✅ Hybrid Audit Complete — Triage Matrix Updated!", state="complete", expanded=False)

    if run_audit:
        st.toast("Audit scan completed! New findings loaded.", icon="🛡️")

# Retrieve active scan state
evaluated_df = st.session_state["evaluated_df"]
finops = st.session_state["finops"]
history_df = st.session_state["history_df"]

security_df = evaluated_df[evaluated_df["violation_category"] == "SECURITY_BREACH"]
cost_df = evaluated_df[evaluated_df["violation_category"] == "COST_DRAIN"]
healthy_count = int((evaluated_df["violation_category"] == "HEALTHY").sum())

# --- EXECUTIVE KPI METRICS ROW ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("💳 Total Monthly Spend", f"${finops['total_monthly_spend']:,.2f}", delta=f"{finops['total_resources']} Active Assets")
col2.metric("🔥 Monthly Money Bleed", f"${finops['wasted_monthly_spend']:,.2f}/mo", delta=f"-{len(cost_df)} Wasteful Nodes", delta_color="inverse")
col3.metric("💰 Projected Annual Savings", f"${finops['projected_annual_savings']:,.2f}/yr", delta="Actionable Recovery")
col4.metric("🚨 Security Breaches", f"{len(security_df)} Critical", delta=f"{healthy_count} Healthy Nodes", delta_color="normal")

st.markdown("<br>", unsafe_allow_html=True)

# --- PERSONA TABS ---
tab_devops, tab_cfo, tab_history = st.tabs([
    "🛡️ DevOps Triage & Safe CLI Remedies",
    "💰 CFO FinOps & Interactive Visuals",
    "📈 Historical Audit Time-Series"
])

with tab_devops:
    st.markdown('### 🔴 Critical Security Breaches <span class="badge-critical">IMMEDIATE ACTION</span>', unsafe_allow_html=True)
    if security_df.empty:
        st.success("✅ Zero public buckets or Shadow IT exposures detected.")
    else:
        for _, row in security_df.iterrows():
            metrics = json.loads(row["operational_metrics"])
            cmd = BrutalMatrixReporter._generate_safe_remediation(row["resource_id"], row["cloud_provider"], row["resource_type"], row["deployment_region"])
            insight = AIHybridAnalyticsLayer.generate_ai_remediation_insight(row["resource_id"], row["violation_reason"], metrics)
            with st.expander(f"🚨 {row['resource_id']} ({row['cloud_provider'].upper()} • {row['deployment_region']}) — {row['violation_reason']}", expanded=True):
                st.warning(f"**AI Architect Strategy:** {insight}")
                st.code(cmd, language="bash")

with tab_cfo:
    st.subheader("Cloud spend by provider")
    provider_spend = finops["provider_breakdown"]
    if provider_spend:
        provider_df = pd.DataFrame(
            [{"Provider": provider.upper(), "Monthly Spend (USD)": spend}
             for provider, spend in provider_spend.items()]
        )
        st.plotly_chart(
            px.pie(provider_df, names="Provider", values="Monthly Spend (USD)", hole=0.45),
            use_container_width=True
        )
    else:
        st.info("No provider spend data is available for this audit.")

    st.subheader("Identified monthly savings")
    waste_df = finops["waste_dataframe"]
    if waste_df.empty:
        st.success("No wasteful resources were identified.")
    else:
        st.dataframe(waste_df, use_container_width=True, hide_index=True)
    st.download_button(
        "Download CFO savings report",
        data=waste_df.to_csv(index=False).encode("utf-8"),
        file_name="cfo_savings_report.csv",
        mime="text/csv",
        disabled=waste_df.empty
    )

with tab_history:
    st.subheader("Historical audit trends")
    if history_df.empty:
        st.info("Historical data will appear after the first audit run.")
    else:
        history = history_df.copy()
        history["scan_timestamp"] = pd.to_datetime(history["scan_timestamp"])
        history = history.sort_values("scan_timestamp")
        st.plotly_chart(
            px.line(
                history,
                x="scan_timestamp",
                y=["total_monthly_spend", "wasted_monthly_spend"],
                markers=True,
                labels={
                    "scan_timestamp": "Audit time",
                    "value": "USD",
                    "variable": "Metric"
                },
                title="Monthly spend and identified waste"
            ),
            use_container_width=True
        )
        st.plotly_chart(
            px.line(
                history,
                x="scan_timestamp",
                y=["total_resources", "security_alerts"],
                markers=True,
                labels={
                    "scan_timestamp": "Audit time",
                    "value": "Count",
                    "variable": "Metric"
                },
                title="Resource and security-alert counts"
            ),
            use_container_width=True
        )
        st.dataframe(history.sort_values("scan_timestamp", ascending=False),
                     use_container_width=True, hide_index=True)
