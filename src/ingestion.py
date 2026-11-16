import os
import json
import re
import pandas as pd
from src.models import (
    CloudResource, ComputeInstance, BlockStorageVolume,
    ObjectStorageBucket, ManagedDatabase, BillingTransaction
)

class CloudDataIngestor:
    INFRA_COLUMNS = {"resource_id", "resource_type", "provider", "region", "cost_per_month"}
    BILLING_COLUMNS = {"transaction_id", "vendor_name", "total_amount_inr"}
    COLUMN_ALIASES = {
        "assetid": "resource_id",
        "assetname": "resource_id",
        "instanceid": "resource_id",
        "instancename": "resource_id",
        "resourcename": "resource_id",
        "resourceid": "resource_id",
        "vmid": "resource_id",
        "vmname": "resource_id",
        "resourcetype": "resource_type",
        "resourcecategory": "resource_type",
        "assettype": "resource_type",
        "assetcategory": "resource_type",
        "servicetype": "resource_type",
        "servicecategory": "resource_type",
        "service": "resource_type",
        "cloud": "provider",
        "cloudprovider": "provider",
        "cloudserviceprovider": "provider",
        "cloudvendor": "provider",
        "providername": "provider",
        "availabilityzone": "region",
        "deploymentregion": "region",
        "geographicregion": "region",
        "location": "region",
        "regionname": "region",
        "zone": "region",
        "monthlyburnrate": "cost_per_month",
        "monthlycost": "cost_per_month",
        "monthlycostinr": "cost_per_month",
        "monthlycostusd": "cost_per_month",
        "monthlyspend": "cost_per_month",
        "monthlyexpenditure": "cost_per_month",
        "totalcost": "cost_per_month",
        "totalcostusd": "cost_per_month",
        "cost": "cost_per_month",
        "costinr": "cost_per_month",
        "amount": "cost_per_month",
        "costusd": "cost_per_month",
        "transactionid": "transaction_id",
        "vendorname": "vendor_name",
        "totalamountinr": "total_amount_inr",
        "baseamountinr": "base_amount_inr",
        "gstamountinr": "gst_amount_inr",
        "invoicenumber": "invoice_number",
        "receiptattached": "receipt_attached",
        "dayofweek": "day_of_week",
    }
    RESOURCE_TYPE_ALIASES = {
        "amazon_ec2": "compute",
        "compute_engine": "compute",
        "ec2": "compute",
        "server": "compute",
        "vm": "compute",
        "virtualmachine": "compute",
        "virtual_machine": "compute",
        "compute_instance": "compute",
        "ebs": "storage",
        "ebs_volume": "storage",
        "disk": "storage",
        "volume": "storage",
        "block_storage": "storage",
        "object_storage": "bucket",
        "object_storage_bucket": "bucket",
        "s3": "bucket",
        "s3_bucket": "bucket",
        "cloud_storage": "bucket",
        "rds": "database",
        "managed_database": "database",
        "sql": "database",
    }

    @classmethod
    def _normalize_columns(cls, df: pd.DataFrame) -> pd.DataFrame:
        normalized_names = {}
        for column in df.columns:
            normalized = re.sub(r"[^a-z0-9]+", "_", str(column).strip().lower()).strip("_")
            compact = normalized.replace("_", "")
            canonical = cls.COLUMN_ALIASES.get(compact, normalized)
            if canonical in normalized_names:
                previous = normalized_names[canonical]
                raise ValueError(
                    f"Ambiguous CSV columns '{previous}' and '{column}' both map to '{canonical}'. "
                    "Keep only one of these columns."
                )
            normalized_names[canonical] = str(column)

        return df.rename(columns={
            original: canonical
            for canonical, original in normalized_names.items()
        })

    @staticmethod
    def _parse_bool(val, default: bool) -> bool:
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            return val.strip().lower() in {"true", "1", "yes"}
        return bool(val) if pd.notna(val) else default

    @classmethod
    def ingest_from_file(cls, file_path: str) -> list[CloudResource]:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Ingestion Error: File not found at '{file_path}'")

        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".csv":
            df = pd.read_csv(file_path)
        elif ext == ".json":
            df = pd.read_json(file_path)
        else:
            raise ValueError(f"Unsupported file format '{ext}'. Only .csv and .json are supported.")

        df = cls._normalize_columns(df)

        # Auto-Detect Schema 1: Corporate & Cloud Billing Ledger CSV
        if cls.BILLING_COLUMNS.issubset(set(df.columns)):
            return cls._ingest_billing_ledger(df)

        # Auto-Detect Schema 2: Cloud Infrastructure Inventory CSV/JSON
        missing_cols = cls.INFRA_COLUMNS - set(df.columns)
        if missing_cols:
            missing = ", ".join(sorted(missing_cols))
            raise ValueError(
                f"Unsupported inventory schema. Could not identify these required fields: {missing}. "
                "Use columns for resource ID, resource type, cloud provider, region, and monthly cost. "
                "Headers such as 'Resource ID', 'Service Type', 'Cloud Provider', 'Location', "
                "and 'Monthly Cost' are supported."
            )

        validated_resources: list[CloudResource] = []
        for row_number, (_, row) in enumerate(df.iterrows(), start=2):
            res_id = str(row["resource_id"]).strip()
            if not res_id or res_id.lower() == "nan":
                raise ValueError(f"Missing resource ID on CSV row {row_number}.")

            res_type = str(row["resource_type"]).strip().lower().replace(" ", "_")
            res_type = cls.RESOURCE_TYPE_ALIASES.get(res_type, res_type)
            provider = str(row["provider"]).strip().lower()
            region = str(row["region"]).strip() if pd.notna(row["region"]) else "unknown-region"
            cost = max(0.0, float(row["cost_per_month"])) if pd.notna(row["cost_per_month"]) else 0.0

            raw_tags = row.get("tags", "{}")
            tags = raw_tags if isinstance(raw_tags, dict) else (json.loads(str(raw_tags)) if pd.notna(raw_tags) and str(raw_tags).strip() else {})

            if res_type == "compute":
                validated_resources.append(ComputeInstance(res_id, provider, region, cost, tags, str(row.get("instance_type", "unknown")), float(row.get("cpu_utilization", 50.0))))
            elif res_type == "storage":
                validated_resources.append(BlockStorageVolume(res_id, provider, region, cost, tags, int(row.get("size_gb", 50)), cls._parse_bool(row.get("is_attached"), True)))
            elif res_type == "bucket":
                validated_resources.append(ObjectStorageBucket(res_id, provider, region, cost, tags, cls._parse_bool(row.get("is_public"), False), int(row.get("size_gb", 10))))
            elif res_type == "database":
                validated_resources.append(ManagedDatabase(res_id, provider, region, cost, tags, str(row.get("db_engine", "postgres")), int(row.get("active_connections", 5))))
            else:
                raise ValueError(
                    f"Unsupported resource type '{row['resource_type']}' on CSV row {row_number}. "
                    "Supported types: Compute, Storage, Bucket, Database."
                )

        return validated_resources

    @classmethod
    def _ingest_billing_ledger(cls, df: pd.DataFrame) -> list[CloudResource]:
        transactions: list[CloudResource] = []
        for _, row in df.iterrows():
            txn_id = str(row["transaction_id"]).strip()
            vendor = str(row["vendor_name"]).strip()
            dept = str(row.get("department", "General")).strip()
            category = str(row.get("category", "General")).strip()
            invoice = str(row.get("invoice_number", "N/A")).strip()
            base_amt = float(row.get("base_amount_inr", 0.0)) if pd.notna(row.get("base_amount_inr")) else 0.0
            gst_amt = float(row.get("gst_amount_inr", 0.0)) if pd.notna(row.get("gst_amount_inr")) else 0.0
            total_amt = max(0.0, float(row.get("total_amount_inr", 0.0))) if pd.notna(row.get("total_amount_inr")) else 0.0
            approver = str(row.get("approver", "PENDING")).strip()
            receipt = cls._parse_bool(row.get("receipt_attached"), False)
            day = str(row.get("day_of_week", "Monday")).strip()
            date_str = str(row.get("date", "")).strip()

            tags = {"Department": dept, "Date": date_str, "Vendor": vendor}
            transactions.append(
                BillingTransaction(txn_id, vendor, dept, total_amt, tags, invoice, base_amt, gst_amt, approver, receipt, day, category)
            )
        return transactions

    @staticmethod
    def generate_sample_real_csv(output_path: str = "database/sample_cloud_export.csv"):
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        sample_data = [
            {"resource_id": "i-09f8e7d6c5b4a3210", "resource_type": "Compute", "provider": "aws", "region": "ap-south-1", "cost_per_month": 540.00, "tags": "{}", "instance_type": "r5.2xlarge", "cpu_utilization": 0.4},
            {"resource_id": "company-customer-backups-2026", "resource_type": "Bucket", "provider": "aws", "region": "ap-south-1", "cost_per_month": 45.00, "tags": '{"Owner": "DataOps"}', "is_public": True, "size_gb": 1200},
            {"resource_id": "staging-analytics-rds-01", "resource_type": "Database", "provider": "aws", "region": "us-east-1", "cost_per_month": 620.00, "tags": '{"Environment": "Staging"}', "db_engine": "postgres-15", "active_connections": 0}
        ]
        pd.DataFrame(sample_data).to_csv(output_path, index=False)
