import os
import pandas as pd

class FinOpsAnalyticsEngine:
    @staticmethod
    def calculate_executive_metrics(evaluated_df: pd.DataFrame) -> dict:
        total_monthly_spend = float(evaluated_df['monthly_burn_rate'].sum())
        waste_df = evaluated_df[evaluated_df['is_waste'] == True].copy()
        wasted_monthly_spend = float(waste_df['monthly_burn_rate'].sum())

        export_records = pd.DataFrame({
            "Resource_ID": waste_df['resource_id'],
            "Provider": waste_df['cloud_provider'].str.upper(),
            "Region": waste_df['deployment_region'],
            "Type": waste_df['resource_type'],
            "Monthly_Waste_USD": waste_df['monthly_burn_rate'].round(2),
            "Annual_Savings_USD": (waste_df['monthly_burn_rate'] * 12).round(2),
            "Violation_Reason": waste_df['violation_reason']
        })

        provider_breakdown = evaluated_df.groupby('cloud_provider')['monthly_burn_rate'].sum().to_dict()

        return {
            "total_resources": len(evaluated_df),
            "total_monthly_spend": round(total_monthly_spend, 2),
            "wasted_monthly_spend": round(wasted_monthly_spend, 2),
            "projected_annual_savings": round(wasted_monthly_spend * 12, 2),
            "provider_breakdown": provider_breakdown,
            "waste_dataframe": export_records
        }

    @staticmethod
    def export_cfo_csv_report(waste_df: pd.DataFrame, output_path: str = "database/cfo_savings_report.csv"):
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        if not waste_df.empty:
            waste_df.to_csv(output_path, index=False)
