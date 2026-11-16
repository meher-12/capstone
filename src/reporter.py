import json
import pandas as pd
from src.ai_layer import AIHybridAnalyticsLayer

class BrutalMatrixReporter:
    @staticmethod
    def _generate_safe_remediation(resource_id: str, provider: str, resource_type: str, region: str) -> str:
        provider = provider.lower()
        if resource_type == "Compute":
            return f"aws ec2 stop-instances --instance-ids {resource_id} --region {region}" if provider == "aws" else f"gcloud compute instances stop {resource_id} --zone={region} --quiet"
        elif resource_type == "Storage":
            return f"aws ec2 create-snapshot --volume-id {resource_id} --region {region} --description 'Pre-cleanup backup'" if provider == "aws" else f"gcloud compute disks snapshot {resource_id} --zone={region} --quiet"
        elif resource_type == "Bucket":
            return f"aws s3api put-public-access-block --bucket {resource_id} --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true" if provider == "aws" else f"gsutil iam ch -d allUsers:objectViewer gs://{resource_id}"
        elif resource_type == "Database":
            return f"aws rds stop-db-instance --db-instance-identifier {resource_id} --region {region}" if provider == "aws" else f"gcloud sql instances patch {resource_id} --activation-policy=NEVER"
        elif resource_type == "Billing":
            return f"finops-cli hold-payout --txn-id {resource_id} --department '{region}' --notify-cfo"
        return "# Manual review required"

    @classmethod
    def render_triage_dashboard(cls, evaluated_df: pd.DataFrame, mode: str = "all", limit: int = None):
        security_df = evaluated_df[evaluated_df['violation_category'] == "SECURITY_BREACH"]
        cost_df = evaluated_df[evaluated_df['violation_category'] == "COST_DRAIN"]
        healthy_count = (evaluated_df['violation_category'] == "HEALTHY").sum()

        if limit is not None:
            security_df = security_df.head(limit)
            cost_df = cost_df.head(limit)

        print("\n" + "█"*90)
        print(" 🚨 HYBRID AUTOMATED CLOUD AUDITOR TRIAGE MATRIX 🚨 ")
        print("█"*90)

        if mode.lower() in ["all", "security"]:
            print(f"\n🔴 [CRITICAL SECURITY & POLICY BREACHES] - Attention required: DevOps / Compliance ({len(security_df)} Shown)")
            print("="*90)
            if security_df.empty:
                print(" ✅ Zero context exposures or policy violations identified.")
            else:
                for _, row in security_df.iterrows():
                    metrics = json.loads(row['operational_metrics'])
                    cmd = cls._generate_safe_remediation(row['resource_id'], row['cloud_provider'], row['resource_type'], row['deployment_region'])
                    insight = AIHybridAnalyticsLayer.generate_ai_remediation_insight(row['resource_id'], row['violation_reason'], metrics)
                    print(f" 📍 Asset Target:  {row['resource_id']}")
                    print(f"    Context Issue: {row['violation_reason']}")
                    print(f"    Strategy:      \033[93m{insight}\033[0m")
                    print(f"    Safe Remedy:   \033[96m{cmd}\033[0m\n")

        if mode.lower() in ["all", "cost"]:
            print(f"\n💵 [DIRECT MONEY DRAINS] - Attention required: FinOps / CFO Board ({len(cost_df)} Shown)")
            print("="*90)
            if cost_df.empty:
                print(" ✅ Zero idle leaks or duplicate/tax errors identified.")
            else:
                for _, row in cost_df.iterrows():
                    metrics = json.loads(row['operational_metrics'])
                    cmd = cls._generate_safe_remediation(row['resource_id'], row['cloud_provider'], row['resource_type'], row['deployment_region'])
                    insight = AIHybridAnalyticsLayer.generate_ai_remediation_insight(row['resource_id'], row['violation_reason'], metrics)
                    print(f" 📍 Asset Target:  {row['resource_id']}")
                    print(f"    Waste Factor:  {row['violation_reason']} (${row['monthly_burn_rate']:,.2f})")
                    print(f"    Strategy:      \033[93m{insight}\033[0m")
                    print(f"    Safe Remedy:   \033[92m{cmd}\033[0m\n")

        print("-" * 90)
        print(f" 🛡️  Audit Summary: Healthy Nodes: {healthy_count} | Mode: {mode.upper()} | Limit: {limit if limit else 'ALL'}")
        print("█"*90 + "\n")
