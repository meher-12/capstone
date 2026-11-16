import random
from src.models import (
    ComputeInstance, BlockStorageVolume, ObjectStorageBucket, ManagedDatabase
)

class StructuralDiscoveryEngine:
    @staticmethod
    def run_discovery_sweep(scale_count: int = 120) -> list:
        discovered_pool = [
            BlockStorageVolume("vol-08fa72bc9a1", "aws", "us-east-1", 320.00, {"Environment": "Production"}, 1000, False),
            ComputeInstance("i-0abc1234567def", "aws", "eu-west-1", 640.00, {}, "c5.4xlarge", 0.4),
            ComputeInstance("instance-9988-prod-gcp", "gcp", "us-central1", 890.00, {"UnregulatedExploit": "true"}, "n2-highcpu-32", 97.8),
            ObjectStorageBucket("prod-customer-invoices-s3", "aws", "us-east-1", 55.00, {"Owner": "Finance"}, True, 850),
            ManagedDatabase("qa-loadtest-postgres-db", "aws", "us-west-2", 520.00, {"Environment": "QA"}, "postgres-15", 0)
        ]

        regions_pool = ["us-east-1", "us-west-2", "eu-central-1", "ap-south-1"]
        providers_pool = ["aws", "gcp"]
        instance_types = ["t3.micro", "t3.medium", "m5.large", "n1-standard-1", "n1-standard-4"]

        for counter in range(scale_count):
            provider = random.choice(providers_pool)
            region = random.choice(regions_pool)
            
            if random.choice(["Compute", "Storage"]) == "Compute":
                is_idle = random.random() < 0.05
                cpu = random.uniform(0.1, 1.5) if is_idle else random.uniform(15.0, 75.0)
                cost = random.uniform(150.0, 500.0) if is_idle else random.uniform(15.0, 120.0)
                tags = {"Owner": "R&D", "Environment": "Prod"} if not is_idle else {}
                discovered_pool.append(ComputeInstance(
                    f"i-mock-{counter:05d}", provider, region, cost, tags, random.choice(instance_types), cpu
                ))
            else:
                is_detached = random.random() < 0.08
                cost = random.uniform(80.0, 250.0) if is_detached else random.uniform(5.0, 45.0)
                tags = {"Owner": "Ops", "Environment": "Prod"}
                discovered_pool.append(BlockStorageVolume(
                    f"vol-mock-{counter:05d}", provider, region, cost, tags, random.choice([50, 100, 250]), not is_detached
                ))

        return discovered_pool
