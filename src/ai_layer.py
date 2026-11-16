import os
import json
import pandas as pd
from sklearn.ensemble import IsolationForest

try:
    from google import genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

class AIHybridAnalyticsLayer:
    REQUIRED_GOVERNANCE_TAGS = {"Owner", "Environment"}

    @classmethod
    def run_hybrid_evaluation(cls, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df['violation_category'] = "HEALTHY"
        df['violation_reason'] = "Normal operational baseline"
        df['is_waste'] = False

        # 1. Unsupervised ML (Isolation Forest) on Compute Nodes
        compute_mask = df['resource_type'] == "Compute"
        ml_anomalies = set()

        if compute_mask.sum() >= 5:
            compute_df = df[compute_mask].copy()
            compute_df['cpu'] = compute_df['operational_metrics'].apply(
                lambda x: json.loads(x).get('cpu_utilization', 50.0)
            )
            features = compute_df[['monthly_burn_rate', 'cpu']]
            iso_forest = IsolationForest(contamination=0.08, random_state=42)
            compute_df['anomaly_score'] = iso_forest.fit_predict(features)
            outliers = compute_df[(compute_df['anomaly_score'] == -1) & (compute_df['cpu'] < 25.0)]
            ml_anomalies = set(outliers['resource_id'].tolist())

        # Pre-compute same-day vendor totals for Threshold Splitting checks
        billing_mask = df['resource_type'] == "Billing"
        split_keys = set()
        if billing_mask.sum() > 0:
            b_df = df[billing_mask].copy()
            b_df['date'] = b_df['metadata_tags'].apply(lambda x: json.loads(x).get('Date', ''))
            grouped = b_df.groupby(['cloud_provider', 'date'])['monthly_burn_rate'].agg(['count', 'sum'])
            for (prov, dt), g_row in grouped.iterrows():
                if g_row['count'] > 1 and g_row['sum'] > 50000:
                    split_keys.add((prov, dt))

        seen_invoices = set()

        # 2. Evaluate Governance, ML & Forensic Rules
        for idx, row in df.iterrows():
            metrics = json.loads(row['operational_metrics'])
            tags = json.loads(row['metadata_tags'])
            res_id = row['resource_id']
            res_type = row['resource_type']
            provider = row['cloud_provider'].upper()

            if res_type == "Bucket" and metrics.get('is_public', False):
                df.at[idx, 'violation_category'] = "SECURITY_BREACH"
                df.at[idx, 'violation_reason'] = f"Publicly Exposed {provider} Bucket ({metrics.get('size_gb')} GB)"
                continue

            if res_type == "Database" and metrics.get('active_connections', 1) == 0:
                df.at[idx, 'violation_category'] = "COST_DRAIN"
                df.at[idx, 'violation_reason'] = f"Idle {provider} {metrics.get('db_engine')} DB (0 active connections)"
                df.at[idx, 'is_waste'] = True
                continue

            if res_type == "Storage" and not metrics.get('is_attached', True):
                df.at[idx, 'violation_category'] = "COST_DRAIN"
                df.at[idx, 'violation_reason'] = f"Orphaned {provider} Disk ({metrics.get('size_gb')} GB)"
                df.at[idx, 'is_waste'] = True
                continue

            if res_type == "Compute":
                cpu = metrics.get('cpu_utilization', 100.0)
                missing_tags = cls.REQUIRED_GOVERNANCE_TAGS - set(tags.keys())

                if cpu > 80.0 and missing_tags:
                    df.at[idx, 'violation_category'] = "SECURITY_BREACH"
                    df.at[idx, 'violation_reason'] = f"Shadow IT Host ({cpu:.1f}% CPU) missing tags: {', '.join(missing_tags)}"
                    continue

                if cpu < 1.0:
                    df.at[idx, 'violation_category'] = "COST_DRAIN"
                    df.at[idx, 'violation_reason'] = f"Zombie Idle Server ({metrics.get('instance_type')}) at {cpu:.1f}% CPU"
                    df.at[idx, 'is_waste'] = True
                    continue

                if res_id in ml_anomalies:
                    df.at[idx, 'violation_category'] = "COST_DRAIN"
                    df.at[idx, 'violation_reason'] = f"ML Cost-to-CPU Outlier ({metrics.get('instance_type')} at {cpu:.1f}% CPU)"
                    df.at[idx, 'is_waste'] = True

            if res_type == "Billing":
                base_amt = metrics.get("base_amount", 0.0)
                gst_amt = metrics.get("gst_amount", 0.0)
                approver = metrics.get("approver", "")
                receipt = metrics.get("receipt_attached", True)
                invoice = metrics.get("invoice_number", "")
                day = metrics.get("day_of_week", "")
                date_str = tags.get("Date", "")

                # 1. Unapproved high-risk vendor or missing receipt
                if approver == "PENDING" or not receipt:
                    df.at[idx, 'violation_category'] = "SECURITY_BREACH"
                    df.at[idx, 'violation_reason'] = f"Unapproved High-Risk Payout ({approver}) / Missing Receipt ({provider})"
                    df.at[idx, 'is_waste'] = True
                    continue

                # 2. Duplicate Invoice (only flag subsequent occurrences, keep first clean)
                inv_key = (provider, invoice)
                if invoice and inv_key in seen_invoices:
                    df.at[idx, 'violation_category'] = "COST_DRAIN"
                    df.at[idx, 'violation_reason'] = f"Duplicate Invoice Resubmission ({invoice}) — {provider}"
                    df.at[idx, 'is_waste'] = True
                    continue
                if invoice:
                    seen_invoices.add(inv_key)

                # 3. Threshold Splitting
                if (row['cloud_provider'], date_str) in split_keys:
                    df.at[idx, 'violation_category'] = "SECURITY_BREACH"
                    df.at[idx, 'violation_reason'] = f"Threshold Splitting Detected ({invoice}) to Bypass Approval Limit ({provider})"
                    df.at[idx, 'is_waste'] = True
                    continue

                # 4. Tax Calculation Error (Standard GST is 18%)
                if base_amt > 0 and abs((gst_amt / base_amt) - 0.18) > 0.02:
                    df.at[idx, 'violation_category'] = "COST_DRAIN"
                    df.at[idx, 'violation_reason'] = f"GST Tax Calculation Mismatch ({round((gst_amt/base_amt)*100)}% vs 18%) — {provider}"
                    df.at[idx, 'is_waste'] = True
                    continue

                # 5. Weekend Policy Violation
                if day == "Sunday" and row['monthly_burn_rate'] > 50000:
                    df.at[idx, 'violation_category'] = "SECURITY_BREACH"
                    df.at[idx, 'violation_reason'] = f"Weekend Policy Violation ({day} High Spend) — {provider}"
                    df.at[idx, 'is_waste'] = True
                    continue

        return df

    @staticmethod
    def generate_ai_remediation_insight(resource_id: str, issue_summary: str, metrics: dict) -> str:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not GENAI_AVAILABLE or not api_key:
            instance_type = metrics.get("instance_type", "")
            if "xlarge" in instance_type or "32" in instance_type:
                return "Heuristic Advice: Over-provisioned tier detected. Downsize to t3.medium to cut costs by ~75%."
            if metrics.get("is_public"):
                return "Heuristic Advice: Block all public ACLs immediately to prevent data exfiltration."
            if "invoice_number" in metrics:
                return "Heuristic Advice: Freeze vendor disbursement immediately and escalate invoice to CFO audit queue."
            return "Heuristic Advice: Snapshot or verify resource ownership before executing cleanup."

        try:
            client = genai.Client(api_key=api_key)
            prompt = (
                f"You are a Cloud FinOps & Security Architect. In 1 short sentence (max 20 words), "
                f"explain the risk and remediation advice for '{resource_id}': "
                f"{issue_summary}. Metrics: {json.dumps(metrics)}"
            )
            response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
            return f"AI Insight: {response.text.strip()}"
        except Exception:
            return "Heuristic Advice (API Fallback): Immediate rightsizing or isolation recommended."
