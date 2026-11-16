import sqlite3
import json
from datetime import datetime
import pandas as pd
from src.models import (
    ComputeInstance, BlockStorageVolume, ObjectStorageBucket,
    ManagedDatabase, BillingTransaction
)

class DatabaseManager:
    def __init__(self, db_path: str = "database/audit_store.db"):
        self.db_path = db_path
        self._orchestrate_schema()

    def _orchestrate_schema(self):
        with sqlite3.connect(self.db_path) as connection:
            cursor = connection.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS inventory_cache (
                    resource_id TEXT PRIMARY KEY,
                    resource_type TEXT NOT NULL,
                    cloud_provider TEXT NOT NULL,
                    deployment_region TEXT NOT NULL,
                    monthly_burn_rate REAL NOT NULL,
                    metadata_tags TEXT NOT NULL,
                    operational_metrics TEXT NOT NULL
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audit_runs (
                    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scan_timestamp TEXT NOT NULL,
                    data_source TEXT NOT NULL,
                    total_resources INTEGER NOT NULL,
                    total_monthly_spend REAL NOT NULL,
                    wasted_monthly_spend REAL NOT NULL,
                    security_alerts INTEGER NOT NULL
                )
            ''')
            connection.commit()

    def clear_stale_records(self):
        with sqlite3.connect(self.db_path) as connection:
            connection.execute("DELETE FROM inventory_cache")
            connection.commit()

    def pipeline_resource_ingestion(self, resource_list: list):
        with sqlite3.connect(self.db_path) as connection:
            cursor = connection.cursor()
            for asset in resource_list:
                if isinstance(asset, ComputeInstance):
                    inferred_type = "Compute"
                    metric_payload = {
                        "instance_type": asset.instance_type,
                        "cpu_utilization": asset.cpu_utilization
                    }
                elif isinstance(asset, BlockStorageVolume):
                    inferred_type = "Storage"
                    metric_payload = {
                        "size_gb": asset.size_gb,
                        "is_attached": asset.is_attached
                    }
                elif isinstance(asset, ObjectStorageBucket):
                    inferred_type = "Bucket"
                    metric_payload = {
                        "is_public": asset.is_public,
                        "size_gb": asset.size_gb
                    }
                elif isinstance(asset, ManagedDatabase):
                    inferred_type = "Database"
                    metric_payload = {
                        "db_engine": asset.db_engine,
                        "active_connections": asset.active_connections
                    }
                elif isinstance(asset, BillingTransaction):
                    inferred_type = "Billing"
                    metric_payload = {
                        "invoice_number": asset.invoice_number,
                        "base_amount": asset.base_amount,
                        "gst_amount": asset.gst_amount,
                        "approver": asset.approver,
                        "receipt_attached": asset.receipt_attached,
                        "day_of_week": asset.day_of_week,
                        "category": asset.category
                    }
                else:
                    continue

                cursor.execute('''
                    INSERT OR REPLACE INTO inventory_cache (
                        resource_id, resource_type, cloud_provider, 
                        deployment_region, monthly_burn_rate, metadata_tags, operational_metrics
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    asset.resource_id,
                    inferred_type,
                    asset.provider,
                    asset.region,
                    asset.cost_per_month,
                    json.dumps(asset.tags),
                    json.dumps(metric_payload)
                ))
            connection.commit()

    def log_audit_run(self, data_source: str, total_resources: int, total_spend: float, wasted_spend: float, security_alerts: int):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with sqlite3.connect(self.db_path) as connection:
            connection.execute('''
                INSERT INTO audit_runs (
                    scan_timestamp, data_source, total_resources, 
                    total_monthly_spend, wasted_monthly_spend, security_alerts
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (timestamp, data_source, total_resources, total_spend, wasted_spend, security_alerts))
            connection.commit()

    def harvest_analytical_dataframe(self) -> pd.DataFrame:
        with sqlite3.connect(self.db_path) as connection:
            return pd.read_sql_query("SELECT * FROM inventory_cache", connection)

    def fetch_historical_runs(self) -> pd.DataFrame:
        with sqlite3.connect(self.db_path) as connection:
            return pd.read_sql_query("SELECT * FROM audit_runs ORDER BY run_id DESC", connection)

    def execute_readonly_sql(self, sql_query: str) -> pd.DataFrame:
        cleaned = sql_query.strip().upper()
        if not cleaned.startswith("SELECT"):
            raise ValueError("Security Guardrail: Only SELECT queries are permitted in the Admin Console.")
        with sqlite3.connect(self.db_path) as connection:
            return pd.read_sql_query(sql_query, connection)
