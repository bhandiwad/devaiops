from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Protocol

from models.identity import Principal, PrincipalContext


@dataclass
class ClusterAccess:
    kubeconfig: str | None = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CapabilityReport:
    capabilities: Dict[str, Any]
    warnings: List[str] = field(default_factory=list)


@dataclass
class BootstrapResult:
    status: str
    detail: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ClusterRef:
    cluster_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProjectRef:
    project_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AppRef:
    app_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AppStatus:
    status: str
    detail: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SyncResult:
    status: str
    detail: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RobotCredentials:
    username: str
    secret_ref: str


@dataclass
class LogResult:
    entries: List[Dict[str, Any]]


@dataclass
class MetricResult:
    series: List[Dict[str, Any]]


@dataclass
class DashboardList:
    dashboards: List[Dict[str, Any]]


@dataclass
class ObservabilitySummary:
    summary: Dict[str, Any]


@dataclass
class RepoRef:
    repo_url: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PRRef:
    pr_url: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PRStatus:
    status: str
    detail: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PRChecks:
    status: str
    checks: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class Snapshot:
    resources: List[Dict[str, Any]]


@dataclass
class Events:
    entries: List[Dict[str, Any]]


@dataclass
class Resource:
    body: Dict[str, Any]


class IdentityAdapter(Protocol):
    """Adapter for identity provider interactions (Keycloak)."""

    def verify_token(self, token: str) -> Principal:
        """Verify token and return principal."""

    def get_context(self, principal: Principal) -> PrincipalContext:
        """Resolve principal context with tenant memberships and roles."""


class ProvisionerAdapter(Protocol):
    """Adapter for provisioning tenant clusters."""

    def provision(self, tenant_spec: Dict[str, Any], provider_profile: Dict[str, Any]) -> ClusterAccess:
        """Provision a new cluster and return access details."""

    def upgrade(self, tenant_id: str, plan: Dict[str, Any]) -> ClusterAccess:
        """Upgrade an existing cluster."""

    def deprovision(self, tenant_id: str) -> None:
        """Deprovision a cluster."""


class CapabilityProbeAdapter(Protocol):
    """Adapter for probing cluster capabilities."""

    def probe(self, cluster_access: ClusterAccess, provider_profile: Dict[str, Any]) -> CapabilityReport:
        """Probe cluster and return capability report."""


class RegistrarAdapter(Protocol):
    """Adapter for bootstrapping tenant cluster resources."""

    def bootstrap(
        self,
        cluster_access: ClusterAccess,
        tenant_spec: Dict[str, Any],
        provider_profile: Dict[str, Any],
        capability_report: CapabilityReport,
    ) -> BootstrapResult:
        """Bootstrap tenant cluster and return result."""


class GitOpsAdapter(Protocol):
    """Adapter for GitOps operations (Argo CD)."""

    def register_cluster(self, tenant_id: str, cluster_access: ClusterAccess, rbac_policy: Dict[str, Any]) -> ClusterRef:
        """Register cluster for GitOps."""

    def ensure_tenant_project(self, tenant_id: str, project_policy: Dict[str, Any]) -> ProjectRef:
        """Ensure tenant project exists."""

    def apply_application(self, app_spec: Dict[str, Any]) -> AppRef:
        """Apply an application spec."""

    def get_application_status(self, app_ref: AppRef) -> AppStatus:
        """Get application status."""

    def sync_application(self, app_ref: AppRef) -> SyncResult:
        """Sync application."""


class SecretsAdapter(Protocol):
    """Adapter for secrets and Vault integration."""

    def ensure_platform_oidc_auth(self, keycloak_config: Dict[str, Any]) -> None:
        """Ensure platform OIDC auth is configured."""

    def ensure_tenant_policies(self, tenant_id: str, role_bindings: Dict[str, Any]) -> None:
        """Ensure tenant policies exist."""

    def ensure_workload_auth(self, tenant_id: str, workload_identity: Dict[str, Any], policy_ref: str) -> None:
        """Ensure workload auth for tenant."""

    def audit_configure(self) -> None:
        """Ensure audit logging is configured."""

    def read_secret(self, secret_ref: str) -> Dict[str, Any]:
        """Read a secret reference and return a dict."""


class RegistryAdapter(Protocol):
    """Adapter for container registry integration (Harbor)."""

    def ensure_tenant_project(self, tenant_id: str, project_spec: Dict[str, Any]) -> ProjectRef:
        """Ensure tenant registry project exists."""

    def ensure_role_bindings(self, tenant_id: str, role_bindings: Dict[str, Any]) -> None:
        """Ensure registry role bindings."""

    def create_robot_account(self, tenant_id: str, scope: Dict[str, Any]) -> RobotCredentials:
        """Create robot account for tenant."""


class ObservabilityAdapter(Protocol):
    """Adapter for observability stack integration."""

    def ensure_tenant_observability(self, tenant_id: str, mode: str, mappings: Dict[str, Any]) -> None:
        """Ensure tenant observability configuration."""

    def query_logs(self, tenant_id: str, query_spec: Dict[str, Any]) -> LogResult:
        """Query tenant logs."""

    def query_metrics(self, tenant_id: str, query_spec: Dict[str, Any]) -> MetricResult:
        """Query tenant metrics."""

    def list_dashboards(self, tenant_id: str) -> DashboardList:
        """List dashboards for tenant."""

    def summary(self, service_ref: Dict[str, Any]) -> ObservabilitySummary:
        """Get summary for service."""


class GitProviderAdapter(Protocol):
    """Adapter for git provider interactions."""

    def scaffold_repo(self, template_ref: Dict[str, Any], parameters: Dict[str, Any]) -> RepoRef:
        """Scaffold a repo from template."""

    def create_pull_request(
        self, repo_ref: RepoRef, branch: str, title: str, body: str, changes: List[Dict[str, Any]]
    ) -> PRRef:
        """Create a pull request."""

    def get_pull_request_status(self, pr_ref: PRRef) -> PRStatus:
        """Get pull request status."""

    def add_labels(self, pr_ref: PRRef, labels: List[str]) -> None:
        """Add labels to a pull request."""

    def get_pull_request_checks(self, pr_ref: PRRef) -> PRChecks:
        """Get status checks for a pull request."""


class K8sAdapter(Protocol):
    """Adapter for Kubernetes access."""

    def get_workload_snapshot(self, cluster_ref: ClusterRef, selectors: Dict[str, Any]) -> Snapshot:
        """Get workload snapshot."""

    def get_events(self, cluster_ref: ClusterRef, namespace: str, since: str | None = None) -> Events:
        """Get events for namespace."""

    def get_resource(self, cluster_ref: ClusterRef, gvk: Dict[str, str], name: str, namespace: str) -> Resource:
        """Get resource from cluster."""


class InvestigatorAdapter(Protocol):
    """Adapter for incident investigation."""

    def investigate(self, evidence_pack: Dict[str, Any]) -> Dict[str, Any]:
        """Produce remediation proposal."""

    def health(self) -> Dict[str, Any]:
        """Return health status."""


@dataclass
class VerificationResult:
    status: str
    detail: Dict[str, Any] = field(default_factory=dict)


class SignatureVerifierAdapter(Protocol):
    """Adapter for signature verification."""

    def verify(self, image_ref: str) -> VerificationResult:
        """Verify signature for an image reference."""


@dataclass
class WebhookDeliveryResult:
    status: str
    detail: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TicketRef:
    ticket_id: str
    url: str | None = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MessageRef:
    message_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class WebhookDestinationAdapter(Protocol):
    def send(self, url: str, payload: Dict[str, Any], headers: Dict[str, str] | None = None) -> WebhookDeliveryResult:
        """Send a webhook payload."""


class TicketingAdapter(Protocol):
    def create_ticket(self, tenant_id: str, payload: Dict[str, Any]) -> TicketRef:
        """Create ticket for incident/lifecycle actions."""

    def update_ticket(self, ticket_ref: TicketRef, payload: Dict[str, Any]) -> TicketRef:
        """Update existing ticket."""


class MessagingAdapter(Protocol):
    def post_message(self, tenant_id: str, payload: Dict[str, Any]) -> MessageRef:
        """Post chat/message notification."""
