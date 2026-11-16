from abc import ABC, abstractmethod

class CloudResource(ABC):
    """
    Abstract Base Class acting as the structural contract for all Cloud & FinOps Resources.
    """
    def __init__(self, resource_id: str, provider: str, region: str, cost_per_month: float, tags: dict):
        if cost_per_month < 0:
            raise ValueError(f"Invalid negative cost ({cost_per_month}) for resource {resource_id}")
        self.resource_id = resource_id
        self.provider = provider.lower()
        self.region = region
        self.cost_per_month = float(cost_per_month)
        self.tags = tags if isinstance(tags, dict) else {}

    @abstractmethod
    def get_remediation_command(self) -> str:
        """Forces every child resource to define a safe, vendor-specific CLI fix."""
        pass

class ComputeInstance(CloudResource):
    """Virtualized servers (AWS EC2, GCP Compute Engine)."""
    def __init__(self, resource_id: str, provider: str, region: str, cost_per_month: float, tags: dict, instance_type: str, cpu_utilization: float):
        super().__init__(resource_id, provider, region, cost_per_month, tags)
        self.instance_type = instance_type
        self.cpu_utilization = float(cpu_utilization)

    def get_remediation_command(self) -> str:
        if self.provider == "aws":
            return f"aws ec2 stop-instances --instance-ids {self.resource_id} --region {self.region}"
        elif self.provider == "gcp":
            return f"gcloud compute instances stop {self.resource_id} --zone={self.region} --quiet"
        return f"# Manual stop recommended for {self.resource_id}"

class BlockStorageVolume(CloudResource):
    """Network block storage disks (AWS EBS, GCP Persistent Disks)."""
    def __init__(self, resource_id: str, provider: str, region: str, cost_per_month: float, tags: dict, size_gb: int, is_attached: bool):
        super().__init__(resource_id, provider, region, cost_per_month, tags)
        self.size_gb = int(size_gb)
        self.is_attached = bool(is_attached)

    def get_remediation_command(self) -> str:
        if self.provider == "aws":
            return f"aws ec2 create-snapshot --volume-id {self.resource_id} --region {self.region} --description 'Pre-cleanup backup'"
        elif self.provider == "gcp":
            return f"gcloud compute disks snapshot {self.resource_id} --zone={self.region} --quiet"
        return f"# Manual snapshot recommended for {self.resource_id}"

class ObjectStorageBucket(CloudResource):
    """Object storage buckets (AWS S3, GCP Cloud Storage)."""
    def __init__(self, resource_id: str, provider: str, region: str, cost_per_month: float, tags: dict, is_public: bool, size_gb: int):
        super().__init__(resource_id, provider, region, cost_per_month, tags)
        self.is_public = bool(is_public)
        self.size_gb = int(size_gb)

    def get_remediation_command(self) -> str:
        if self.provider == "aws":
            return f"aws s3api put-public-access-block --bucket {self.resource_id} --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
        elif self.provider == "gcp":
            return f"gsutil iam ch -d allUsers:objectViewer gs://{self.resource_id}"
        return f"# Restrict public ACLs on bucket {self.resource_id}"

class ManagedDatabase(CloudResource):
    """Managed relational databases (AWS RDS, GCP Cloud SQL)."""
    def __init__(self, resource_id: str, provider: str, region: str, cost_per_month: float, tags: dict, db_engine: str, active_connections: int):
        super().__init__(resource_id, provider, region, cost_per_month, tags)
        self.db_engine = db_engine
        self.active_connections = int(active_connections)

    def get_remediation_command(self) -> str:
        if self.provider == "aws":
            return f"aws rds stop-db-instance --db-instance-identifier {self.resource_id} --region {self.region}"
        elif self.provider == "gcp":
            return f"gcloud sql instances patch {self.resource_id} --activation-policy=NEVER"
        return f"# Pause idle database {self.resource_id}"

class BillingTransaction(CloudResource):
    """Corporate & Cloud Billing Ledger Transactions (e.g., AWS India, Azure, Vendor Invoices)."""
    def __init__(self, resource_id: str, provider: str, region: str, cost_per_month: float, tags: dict,
                 invoice_number: str, base_amount: float, gst_amount: float, approver: str,
                 receipt_attached: bool, day_of_week: str, category: str):
        super().__init__(resource_id, provider, region, cost_per_month, tags)
        self.invoice_number = invoice_number
        self.base_amount = float(base_amount)
        self.gst_amount = float(gst_amount)
        self.approver = approver
        self.receipt_attached = bool(receipt_attached)
        self.day_of_week = day_of_week
        self.category = category

    def get_remediation_command(self) -> str:
        return f"finops-cli hold-payout --txn-id {self.resource_id} --invoice {self.invoice_number} --notify-cfo"
