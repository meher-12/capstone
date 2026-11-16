import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.ingestion import CloudDataIngestor
from src.models import BillingTransaction, ComputeInstance


class TestCloudDataIngestor(unittest.TestCase):
    def test_inventory_accepts_common_csv_header_variations(self):
        data = pd.DataFrame([{
            "Resource Name": "vm-001",
            "Service Category": "Compute Engine",
            "Cloud Service Provider": "AWS",
            "Region Name": "us-east-1",
            "Monthly Cost USD": 24.5,
            "CPU Utilization": 18.0,
        }])

        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "inventory.csv"
            data.to_csv(csv_path, index=False)
            resources = CloudDataIngestor.ingest_from_file(str(csv_path))

        self.assertEqual(len(resources), 1)
        self.assertIsInstance(resources[0], ComputeInstance)
        self.assertEqual(resources[0].resource_id, "vm-001")
        self.assertEqual(resources[0].provider, "aws")
        self.assertEqual(resources[0].cost_per_month, 24.5)

    def test_billing_ledger_accepts_normalized_headers(self):
        data = pd.DataFrame([{
            "Transaction ID": "txn-001",
            "Vendor Name": "Cloud Vendor",
            "Total Amount INR": 118.0,
            "Base Amount INR": 100.0,
            "GST Amount INR": 18.0,
        }])

        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "billing.csv"
            data.to_csv(csv_path, index=False)
            transactions = CloudDataIngestor.ingest_from_file(str(csv_path))

        self.assertEqual(len(transactions), 1)
        self.assertIsInstance(transactions[0], BillingTransaction)
        self.assertEqual(transactions[0].resource_id, "txn-001")
        self.assertEqual(transactions[0].cost_per_month, 118.0)

    def test_unsupported_schema_explains_required_fields(self):
        data = pd.DataFrame([{"Item": "something", "Price": 15}])

        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "unsupported.csv"
            data.to_csv(csv_path, index=False)
            with self.assertRaisesRegex(ValueError, "resource ID, resource type, cloud provider"):
                CloudDataIngestor.ingest_from_file(str(csv_path))


if __name__ == "__main__":
    unittest.main()
