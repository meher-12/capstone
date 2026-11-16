import sys
import os
import argparse
from src.engine import StructuralDiscoveryEngine
from src.ingestion import CloudDataIngestor
from src.db_manager import DatabaseManager
from src.ai_layer import AIHybridAnalyticsLayer
from src.reporter import BrutalMatrixReporter
from src.analytics import FinOpsAnalyticsEngine
from src.notifier import AlertNotifier

def execute_system_pipeline():
    parser = argparse.ArgumentParser(description="Hybrid Automated Cloud Auditor CLI Engine")
    parser.add_argument("--source", type=str, default="mock", choices=["mock", "real"], help="Choose 'mock' simulator or 'real' CSV/JSON file")
    parser.add_argument("--file", type=str, default="database/sample_cloud_export.csv", help="Path to real CSV/JSON inventory file")
    parser.add_argument("--view", type=str, default="all", choices=["all", "security", "cost"], help="Filter triage dashboard output")
    parser.add_argument("--limit", type=int, default=None, help="Limit violations shown per section")
    args = parser.parse_args()

    os.makedirs("database", exist_ok=True)

    # 1. Data Discovery / Ingestion
    if args.source == "real":
        if not os.path.exists(args.file):
            CloudDataIngestor.generate_sample_real_csv(args.file)
        print(f"\n[Step 1/5] Ingesting real cloud inventory from '{args.file}'...")
        discovered_inventory = CloudDataIngestor.ingest_from_file(args.file)
    else:
        print("\n[Step 1/5] Running multi-cloud discovery sweep across simulated nodes...")
        discovered_inventory = StructuralDiscoveryEngine.run_discovery_sweep(scale_count=120)

    # 2. Relational DBMS Sync
    print(f"[Step 2/5] Syncing {len(discovered_inventory)} nodes into SQLite DBMS...")
    db_interface = DatabaseManager()
    db_interface.clear_stale_records()
    db_interface.pipeline_resource_ingestion(discovered_inventory)

    # 3. ML Isolation Forest & Governance Tag Evaluation
    print("[Step 3/5] Running Isolation Forest ML & Governance Tag evaluation...")
    working_df = db_interface.harvest_analytical_dataframe()
    if working_df.empty:
        print(" [!] Execution Terminated: Inventory tracking dataframe is empty.")
        sys.exit(1)

    evaluated_df = AIHybridAnalyticsLayer.run_hybrid_evaluation(working_df)

    # 4. FinOps Metrics, Historical Audit Log & Webhook Alerts
    print("[Step 4/5] Computing FinOps totals, logging history, and dispatching critical alerts...")
    finops_summary = FinOpsAnalyticsEngine.calculate_executive_metrics(evaluated_df)
    FinOpsAnalyticsEngine.export_cfo_csv_report(finops_summary["waste_dataframe"])

    security_count = int((evaluated_df['violation_category'] == "SECURITY_BREACH").sum())
    db_interface.log_audit_run(
        data_source=args.source.upper(),
        total_resources=finops_summary["total_resources"],
        total_spend=finops_summary["total_monthly_spend"],
        wasted_spend=finops_summary["wasted_monthly_spend"],
        security_alerts=security_count
    )
    dispatched_count = AlertNotifier.dispatch_critical_alerts(evaluated_df)

    # 5. Render Triage Dashboard
    print("[Step 5/5] Rendering Brutal Triage Matrix...")
    BrutalMatrixReporter.render_triage_dashboard(evaluated_df, mode=args.view, limit=args.limit)

    print("💰 [CFO EXECUTIVE & OPERATIONS SUMMARY]")
    print(f"   Data Source Mode:           {args.source.upper()}")
    print(f"   Total Monthly Cloud Spend:  ${finops_summary['total_monthly_spend']:,.2f}")
    print(f"   Monthly Money Bleed:        ${finops_summary['wasted_monthly_spend']:,.2f}/mo")
    print(f"   Projected Annual Savings:   ${finops_summary['projected_annual_savings']:,.2f}/yr")
    print(f"   Critical Alerts Dispatched: {dispatched_count} (Saved to database/dispatched_alerts.json)")
    print(f"   CSV Report Exported To:     database/cfo_savings_report.csv\n")

if __name__ == "__main__":
    execute_system_pipeline()
