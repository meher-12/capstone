import unittest
import pandas as pd
from src.models import ComputeInstance, BlockStorageVolume
from src.ai_layer import AIHybridAnalyticsLayer

class TestCloudAuditorCore(unittest.TestCase):
    """
    Automated test suite verifying structural integrity and rules detection models.
    """

    def test_compute_remediation_command_generation(self):
        """Verify that AWS and GCP compute models output the correct terminal payloads."""
        aws_instance = ComputeInstance(
            resource_id="i-test-123", provider="aws", region="us-east-1",
            cost_per_month=100.0, tags={}, instance_type="t3.micro", cpu_utilization=50.0
        )
        gcp_instance = ComputeInstance(
            resource_id="inst-test-123", provider="gcp", region="us-central1-a",
            cost_per_month=200.0, tags={}, instance_type="n1-standard-1", cpu_utilization=40.0
        )

        self.assertIn("terminate-instances", aws_instance.get_remediation_command())
        self.assertIn("delete", gcp_instance.get_remediation_command())

    def test_zombie_server_behavioral_detection(self):
        """Verify that the AI Layer accurately catches abandoned machines running under 1% CPU."""
        mock_row = pd.Series({
            'resource_type': 'Compute',
            'cloud_provider': 'aws',
            'deployment_region': 'us-east-1',
            'monthly_burn_rate': 450.0,
            'metadata_tags': '{}',
            'operational_metrics': '{"instance_type": "m5.xlarge", "cpu_utilization": 0.3}'
        })

        analysis_result = AIHybridAnalyticsLayer.analyze_behavioral_risk_profile(mock_row)
        self.assertEqual(analysis_result, "AI_ANOMALY: ZOMBIE_WORKLOAD_ABANDONMENT")

    def test_shadow_it_detection(self):
        """Verify that highly active compute instances with missing context tags trigger compliance alerts."""
        mock_row = pd.Series({
            'resource_type': 'Compute',
            'cloud_provider': 'gcp',
            'deployment_region': 'us-west-1',
            'monthly_burn_rate': 800.0,
            'metadata_tags': '{}',
            'operational_metrics': '{"instance_type": "n2-heavy", "cpu_utilization": 92.5}'
        })

        analysis_result = AIHybridAnalyticsLayer.analyze_behavioral_risk_profile(mock_row)
        self.assertEqual(analysis_result, "AI_ANOMALY: SHADOW_IT_COMPLIANCE_BREACH")

if __name__ == "__main__":
    unittest.main()
