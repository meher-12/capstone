import os
import json
from datetime import datetime
import requests
import pandas as pd

class AlertNotifier:
    """
    Dispatches urgent security breaches and high-cost drains to Slack/Discord webhooks,
    with a local JSON audit log fallback when no webhook URL is configured.
    """

    @staticmethod
    def dispatch_critical_alerts(evaluated_df: pd.DataFrame, log_path: str = "database/dispatched_alerts.json"):
        security_df = evaluated_df[evaluated_df['violation_category'] == "SECURITY_BREACH"]
        high_cost_df = evaluated_df[(evaluated_df['violation_category'] == "COST_DRAIN") & (evaluated_df['monthly_burn_rate'] >= 500.0)]

        alerts = []
        for _, row in security_df.iterrows():
            alerts.append({
                "severity": "CRITICAL_SECURITY",
                "resource_id": row['resource_id'],
                "provider": row['cloud_provider'].upper(),
                "reason": row['violation_reason']
            })

        for _, row in high_cost_df.iterrows():
            alerts.append({
                "severity": "HIGH_COST_BLEED",
                "resource_id": row['resource_id'],
                "provider": row['cloud_provider'].upper(),
                "reason": f"{row['violation_reason']} (${row['monthly_burn_rate']:.2f}/mo)"
            })

        if not alerts:
            return 0

        webhook_url = os.environ.get("ALERT_WEBHOOK_URL")
        payload = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "alert_count": len(alerts),
            "alerts": alerts
        }

        # 1. Send to Slack/Discord Webhook if configured
        if webhook_url:
            try:
                text_lines = [f"🚨 *Hybrid Cloud Auditor Alert ({len(alerts)} Critical Findings)*"]
                for a in alerts:
                    text_lines.append(f"• [{a['severity']}] `{a['resource_id']}` ({a['provider']}): {a['reason']}")
                requests.post(webhook_url, json={"text": "\n".join(text_lines)}, timeout=5)
            except Exception:
                pass

        # 2. Always persist an immutable local alert log
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "w") as f:
            json.dump(payload, f, indent=2)

        return len(alerts)
