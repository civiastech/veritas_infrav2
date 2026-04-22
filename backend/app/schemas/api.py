
from typing import Optional, Any
from pydantic import BaseModel, ConfigDict, Field

class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    mfa_required: bool = False

class LoginRequest(BaseModel):
    email: str
    password: str
    mfa_code: Optional[str] = None

class RefreshRequest(BaseModel):
    refresh_token: str

class MFASetupResponse(BaseModel):
    secret: str
    provisioning_uri: str

class MFAVerifyRequest(BaseModel):
    code: str

class ProfessionalOut(ORMModel):
    id: int
    name: str
    email: str
    band: str
    discipline: Optional[str] = None
    country: Optional[str] = None
    projects: int
    shi_avg: float
    pri_score: float
    role: str
    active: bool
    bio: Optional[str] = None
    mfa_enabled: bool = False

class ProjectBase(BaseModel):
    uid: str
    name: str
    client: Optional[str] = None
    country: Optional[str] = None
    type: Optional[str] = None
    value: float = 0
    currency: str = "USD"
    phase: Optional[str] = None
    status: str = "active"
    progress: float = Field(default=0, ge=0, le=100)
    shi: float = Field(default=0, ge=0, le=100)
    started: Optional[str] = None
    target_completion: Optional[str] = None
    lead_engineer_id: Optional[int] = None
    description: Optional[str] = None

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    client: Optional[str] = None
    country: Optional[str] = None
    type: Optional[str] = None
    value: Optional[float] = None
    currency: Optional[str] = None
    phase: Optional[str] = None
    status: Optional[str] = None
    progress: Optional[float] = Field(default=None, ge=0, le=100)
    shi: Optional[float] = Field(default=None, ge=0, le=100)
    started: Optional[str] = None
    target_completion: Optional[str] = None
    lead_engineer_id: Optional[int] = None
    description: Optional[str] = None

class ProjectOut(ORMModel, ProjectBase):
    id: int

class ComponentBase(BaseModel):
    uid: str
    project_uid: str
    type: Optional[str] = None
    spec: Optional[str] = None
    level: Optional[str] = None
    grid: Optional[str] = None
    shi: float = Field(default=0, ge=0, le=100)
    status: str = "pending"
    material_batch: Optional[str] = None
    executed_by: Optional[int] = None
    approved_by: Optional[int] = None
    notes: Optional[str] = None
    evidence_required: bool = True
    blocked_for_execution: bool = True

class ComponentCreate(ComponentBase):
    pass

class ComponentUpdate(BaseModel):
    type: Optional[str] = None
    spec: Optional[str] = None
    level: Optional[str] = None
    grid: Optional[str] = None
    shi: Optional[float] = Field(default=None, ge=0, le=100)
    status: Optional[str] = None
    material_batch: Optional[str] = None
    executed_by: Optional[int] = None
    approved_by: Optional[int] = None
    notes: Optional[str] = None
    evidence_required: Optional[bool] = None
    blocked_for_execution: Optional[bool] = None

class ComponentOut(ORMModel, ComponentBase):
    id: int

class EvidenceOut(ORMModel):
    id: int
    component_uid: str
    project_uid: str
    type: Optional[str] = None
    images: int
    description: Optional[str] = None
    status: str
    hash: Optional[str] = None
    manifest_hash: Optional[str] = None

class EvidenceAssetOut(ORMModel):
    id: int
    evidence_id: int
    original_name: str
    storage_path: str
    storage_backend: str
    content_type: Optional[str] = None
    sha256: str
    size_bytes: int
    immutable: bool

class InspectionCreate(BaseModel):
    component_uid: str
    material_score: float = Field(ge=0, le=100)
    assembly_score: float = Field(ge=0, le=100)
    env_score: float = Field(ge=0, le=100)
    supervision_score: float = Field(ge=0, le=100)
    ai_flags: int = 0
    reason_tag: Optional[str] = None

class InspectionOut(ORMModel):
    id: int
    component_uid: str
    project_uid: str
    inspector_id: Optional[int] = None
    method_id: Optional[int] = None
    shi: float
    material_score: float
    assembly_score: float
    env_score: float
    supervision_score: float
    ai_flags: int
    reason_tag: Optional[str] = None
    status: str

class MilestoneOut(ORMModel):
    id: int
    project_uid: str
    name: str
    phase: int
    amount: float
    currency: str
    required_shi: float
    status: str
    released_date: Optional[str] = None
    description: Optional[str] = None

class PaymentOut(ORMModel):
    id: int
    project_uid: str
    milestone_id: Optional[int] = None
    amount: float
    currency: str
    from_party: Optional[str] = None
    to_party: Optional[str] = None
    released_by: Optional[str] = None
    date: Optional[str] = None
    tx_id: Optional[str] = None
    status: str
    gate_decision: Optional[str] = None
    gate_reason: Optional[str] = None

class GateDecisionOut(BaseModel):
    project_uid: str
    milestone_id: int
    project_shi: float
    required_shi: float
    eligible: bool
    reason: str

class CertificationIssueRequest(BaseModel):
    project_uid: str
    certificate_type: str = "SEAL-HONOR"
    notes: Optional[str] = None

class CertificationOut(ORMModel):
    id: int
    project_uid: str
    type: str
    shi_composite: float
    issued_by: Optional[int] = None
    co_signed_by: Optional[int] = None
    issued_date: Optional[str] = None
    physical_plate: Optional[str] = None
    status: str
    qr_code: Optional[str] = None
    notes: Optional[str] = None

class PublicCertificateOut(BaseModel):
    project_uid: str
    certificate_type: str
    status: str
    issued_date: Optional[str] = None
    physical_plate: Optional[str] = None
    qr_code: Optional[str] = None
    shi_composite: float

class MaterialBase(BaseModel):
    batch_uid: str
    name: str
    grade: Optional[str] = None
    supplier: Optional[str] = None
    country: Optional[str] = None
    cert_number: Optional[str] = None
    verified: bool = False
    projects_used: Optional[list] = None
    test_strength: float = 0
    required_strength: float = 0
    status: str = "pending"
    suspension_reason: Optional[str] = None

class MaterialCreate(MaterialBase):
    pass

class MaterialUpdate(BaseModel):
    name: Optional[str] = None
    grade: Optional[str] = None
    supplier: Optional[str] = None
    country: Optional[str] = None
    cert_number: Optional[str] = None
    verified: Optional[bool] = None
    projects_used: Optional[list] = None
    test_strength: Optional[float] = None
    required_strength: Optional[float] = None
    status: Optional[str] = None
    suspension_reason: Optional[str] = None

class MaterialOut(ORMModel, MaterialBase):
    id: int

class SensorReadingIn(BaseModel):
    sensor_id: int
    reading: float

class SensorOut(ORMModel):
    id: int
    component_uid: str
    project_uid: str
    type: str
    current_reading: float
    unit: Optional[str] = None
    threshold: float
    status: str
    last_update: Optional[str] = None

class MonitorAlertOut(ORMModel):
    id: int
    sensor_id: int
    project_uid: str
    component_uid: str
    reading: float
    threshold: float
    severity: str
    status: str
    message: str

class DisputeCreate(BaseModel):
    uid: str
    project_uid: str
    component_uid: Optional[str] = None
    type: str
    against_party: Optional[str] = None
    description: str

class DisputeResolve(BaseModel):
    resolution: str

class DisputeOut(ORMModel):
    id: int
    uid: str
    project_uid: Optional[str] = None
    component_uid: Optional[str] = None
    type: Optional[str] = None
    raised_by: Optional[int] = None
    against_party: Optional[str] = None
    description: Optional[str] = None
    status: str
    resolution: Optional[str] = None
    raised_date: Optional[str] = None
    resolved_date: Optional[str] = None
    arbitrator_id: Optional[int] = None
    determination_hash: Optional[str] = None

class TwinEventOut(ORMModel):
    id: int
    event_type: str
    aggregate_type: str
    aggregate_uid: str
    actor_email: Optional[str] = None
    event_index: int
    previous_hash: Optional[str] = None
    current_hash: str
    payload: dict


class TenderBase(BaseModel):
    uid: str
    name: str
    client: Optional[str] = None
    country: Optional[str] = None
    value: float = 0
    currency: str = "USD"
    deadline: Optional[str] = None
    status: str = "open"
    type: Optional[str] = None
    description: Optional[str] = None

class TenderCreate(TenderBase):
    pass

class TenderUpdate(BaseModel):
    name: Optional[str] = None
    client: Optional[str] = None
    country: Optional[str] = None
    value: Optional[float] = None
    currency: Optional[str] = None
    deadline: Optional[str] = None
    status: Optional[str] = None
    type: Optional[str] = None
    description: Optional[str] = None

class TenderOut(ORMModel, TenderBase):
    id: int

class NotificationOut(ORMModel):
    id: int
    type: str
    message: str
    priority: str
    read: bool
    for_role: Optional[list] = None

class DashboardSummary(BaseModel):
    total_projects: int
    active_projects: int
    total_professionals: int
    avg_shi: float
    total_materials: int
    open_tenders: int
    unread_notifications: int
    total_project_value_usd: float
    total_open_alerts: int
    total_certifications: int
    total_twin_events: int

class ApiList(BaseModel):
    items: list[Any]
    total: int

class MutationResult(BaseModel):
    success: bool = True
    message: str

class AuditLogOut(ORMModel):
    id: int
    action: str
    actor: str
    detail: Optional[str] = None
    timestamp: Optional[str] = None
    ip_address: Optional[str] = None
    route: Optional[str] = None


class AtlasSubscriptionBase(BaseModel):
    subscriber_name: str
    subscriber_type: str = "government"
    country_scope: Optional[str] = None
    access_tier: str = "standard"
    status: str = "active"

class AtlasSubscriptionCreate(AtlasSubscriptionBase):
    pass

class AtlasSubscriptionOut(ORMModel, AtlasSubscriptionBase):
    id: int

class AtlasReportCreate(BaseModel):
    title: str
    country_scope: Optional[str] = None
    report_type: str = "portfolio"
    period_label: Optional[str] = None

class AtlasReportOut(ORMModel):
    id: int
    title: str
    country_scope: Optional[str] = None
    report_type: str
    period_label: Optional[str] = None
    generated_by: Optional[int] = None
    payload: dict
    status: str

class AtlasPortfolioSummary(BaseModel):
    total_projects: int
    active_projects: int
    avg_shi: float
    total_project_value: float
    countries: list[dict]
    open_alerts: int
    certified_projects: int
    payment_released_total: float
    professionalism_index_avg: float

class FinancialProductBase(BaseModel):
    code: str
    name: str
    category: str = "insurance"
    description: Optional[str] = None
    base_rate_bps: float = 0
    min_shi: float = 0
    active: bool = True

class FinancialProductCreate(FinancialProductBase):
    pass

class FinancialProductOut(ORMModel, FinancialProductBase):
    id: int

class UnderwritingApplicationCreate(BaseModel):
    application_uid: str
    project_uid: str
    product_code: str
    applicant_name: str
    requested_amount: float
    currency: str = "USD"

class UnderwritingApplicationOut(ORMModel):
    id: int
    application_uid: str
    project_uid: str
    product_code: str
    applicant_name: str
    requested_amount: float
    currency: str
    status: str
    submitted_by: Optional[int] = None

class RiskDecisionOut(ORMModel):
    id: int
    application_id: int
    risk_score: float
    decision: str
    premium_adjustment_bps: float
    rationale: str
    feature_snapshot: dict

class UnderwritingEvaluationOut(BaseModel):
    application: UnderwritingApplicationOut
    decision: RiskDecisionOut

class LearningPathBase(BaseModel):
    code: str
    title: str
    target_band: Optional[str] = None
    discipline_scope: Optional[str] = None
    status: str = "active"
    description: Optional[str] = None

class LearningPathCreate(LearningPathBase):
    pass

class LearningPathOut(ORMModel, LearningPathBase):
    id: int

class CourseBase(BaseModel):
    path_code: str
    code: str
    title: str
    delivery_mode: str = "async"
    hours: int = 1
    status: str = "published"

class CourseCreate(CourseBase):
    pass

class CourseOut(ORMModel, CourseBase):
    id: int

class EnrollmentCreate(BaseModel):
    course_code: str

class EnrollmentOut(ORMModel):
    id: int
    professional_id: int
    course_code: str
    path_code: Optional[str] = None
    status: str
    score: Optional[float] = None

class CompleteEnrollmentRequest(BaseModel):
    score: float = Field(ge=0, le=100)

class CredentialAwardOut(ORMModel):
    id: int
    professional_id: int
    path_code: str
    credential_title: str
    awarded_by: Optional[int] = None
    status: str
    advancement_recommended: bool

class BandAdvancementSummary(BaseModel):
    professional_id: int
    current_band: str
    completed_courses: int
    completed_paths: int
    recommended_next_band: Optional[str] = None
    recommendation_ready: bool


class CountryBase(BaseModel):
    code: str
    name: str
    region: str | None = None
    launch_stage: str = "pipeline"
    readiness_score: float = Field(default=0, ge=0, le=100)
    regulator_appetite: str | None = None
    status: str = "active"

class CountryCreate(CountryBase):
    pass

class CountryOut(ORMModel, CountryBase):
    id: int

class CountryTenantBase(BaseModel):
    country_code: str
    operator_name: str
    license_type: str = "country_franchise"
    revenue_share_pct: float = 0
    launch_status: str = "pending"
    start_date: str | None = None
    end_date: str | None = None

class CountryTenantCreate(CountryTenantBase):
    pass

class CountryTenantOut(ORMModel, CountryTenantBase):
    id: int

class LaunchProgramBase(BaseModel):
    country_code: str
    title: str
    phase: str = "readiness"
    progress: float = Field(default=0, ge=0, le=100)
    owner_professional_id: int | None = None
    status: str = "active"
    notes: str | None = None

class LaunchProgramCreate(LaunchProgramBase):
    pass

class LaunchProgramOut(ORMModel, LaunchProgramBase):
    id: int

class RevenueShareRuleBase(BaseModel):
    country_code: str
    module_code: str
    local_operator_pct: float = 0
    central_platform_pct: float = 0
    government_program_pct: float = 0
    status: str = "active"

class RevenueShareRuleCreate(RevenueShareRuleBase):
    pass

class RevenueShareRuleOut(ORMModel, RevenueShareRuleBase):
    id: int

class CloneRolloutSummary(BaseModel):
    total_countries: int
    active_tenants: int
    avg_readiness: float
    launches_in_progress: int
    countries: list[dict]

class CSTMemberBase(BaseModel):
    professional_id: int
    appointment_title: str = "Council Member"
    voting_rights: bool = True
    term_start: str | None = None
    term_end: str | None = None
    status: str = "active"

class CSTMemberCreate(CSTMemberBase):
    pass

class CSTMemberOut(ORMModel, CSTMemberBase):
    id: int

class GovernanceCommitteeBase(BaseModel):
    code: str
    name: str
    scope: str | None = None
    status: str = "active"

class GovernanceCommitteeCreate(GovernanceCommitteeBase):
    pass

class GovernanceCommitteeOut(ORMModel, GovernanceCommitteeBase):
    id: int

class GovernanceResolutionBase(BaseModel):
    resolution_uid: str
    committee_code: str
    title: str
    resolution_type: str = "standard"
    body_text: str
    status: str = "draft"
    effective_date: str | None = None

class GovernanceResolutionCreate(GovernanceResolutionBase):
    pass

class GovernanceResolutionOut(ORMModel, GovernanceResolutionBase):
    id: int
    issued_by: int | None = None

class GovernanceVoteCreate(BaseModel):
    resolution_uid: str
    vote: str = "yes"
    rationale: str | None = None

class GovernanceVoteOut(ORMModel):
    id: int
    resolution_uid: str
    member_professional_id: int
    vote: str
    rationale: str | None = None

class GovernanceDashboard(BaseModel):
    active_members: int
    active_committees: int
    open_resolutions: int
    passed_resolutions: int
    delegated_authorities: int

class RegulationBase(BaseModel):
    country_code: str
    regulation_code: str
    title: str
    category: str = "construction_integrity"
    status: str = "draft"
    summary: str | None = None

class RegulationCreate(RegulationBase):
    pass

class RegulationOut(ORMModel, RegulationBase):
    id: int

class ConsultationBase(BaseModel):
    consultation_uid: str
    country_code: str
    title: str
    consultation_type: str = "regulatory"
    status: str = "open"
    opened_at_label: str | None = None
    closed_at_label: str | None = None

class ConsultationCreate(ConsultationBase):
    pass

class ConsultationOut(ORMModel, ConsultationBase):
    id: int

class ComplianceMappingBase(BaseModel):
    country_code: str
    standard_code: str
    module_code: str
    requirement_summary: str
    status: str = "mapped"

class ComplianceMappingCreate(ComplianceMappingBase):
    pass

class ComplianceMappingOut(ORMModel, ComplianceMappingBase):
    id: int

class RegulatoryReadinessSummary(BaseModel):
    tracked_countries: int
    open_consultations: int
    mapped_requirements: int
    draft_regulations: int
    countries: list[dict]


class WorkflowDefinitionIn(BaseModel):
    code: str
    name: str
    country_code: Optional[str] = None
    tenant_code: Optional[str] = None
    is_active: bool = True

class WorkflowStateIn(BaseModel):
    workflow_id: int
    code: str
    name: str
    is_initial: bool = False
    is_terminal: bool = False

class WorkflowTransitionIn(BaseModel):
    workflow_id: int
    from_state_code: str
    to_state_code: str
    action_code: str
    required_role: Optional[str] = None
    condition_expr: Optional[str] = None

class WorkflowInstanceIn(BaseModel):
    workflow_code: str
    entity_type: str
    entity_id: str
    current_state_code: str
    country_code: Optional[str] = None
    tenant_code: Optional[str] = None

class WorkflowActionIn(BaseModel):
    action_code: str
    actor: str
    actor_role: Optional[str] = None

class PolicyRuleIn(BaseModel):
    code: str
    action: str
    resource: str
    effect: str = 'allow'
    subject_role: Optional[str] = None
    country_code: Optional[str] = None
    tenant_code: Optional[str] = None
    condition_expr: Optional[str] = None
    is_active: bool = True

class PolicyEvalIn(BaseModel):
    subject: str
    subject_role: Optional[str] = None
    action: str
    resource: str
    country_code: Optional[str] = None
    tenant_code: Optional[str] = None

class FeatureFlagIn(BaseModel):
    code: str
    name: str
    enabled: bool
    environment: Optional[str] = None
    tenant_code: Optional[str] = None
    country_code: Optional[str] = None
    stability: str = 'stable'

class CountryConfigIn(BaseModel):
    country_code: str
    default_workflow_variant: Optional[str] = None
    certification_rule: Optional[str] = None
    payment_rule: Optional[str] = None
    evidence_rule: Optional[str] = None
    regulator_override: bool = False
    config_json: Optional[str] = None
