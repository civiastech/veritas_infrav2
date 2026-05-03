
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Integer, Float, Boolean, Text, ForeignKey, DateTime, JSON, BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class SoftDeleteMixin:
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class Professional(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "professionals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    band: Mapped[str] = mapped_column(String(50))
    discipline: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    projects: Mapped[int] = mapped_column(Integer, default=0)
    shi_avg: Mapped[float] = mapped_column(Float, default=0)
    pri_score: Mapped[float] = mapped_column(Float, default=0)
    role: Mapped[str] = mapped_column(String(50), index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    mfa_secret: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    # PRI 5-component fields (added by migration 0027)
    pri_eqh: Mapped[float] = mapped_column(Float, default=0.0)
    pri_esi: Mapped[float] = mapped_column(Float, default=1.0)
    pri_ar: Mapped[float] = mapped_column(Float, default=1.0)
    pri_sis: Mapped[float] = mapped_column(Float, default=0.0)
    pri_pd: Mapped[float] = mapped_column(Float, default=0.0)
    pri_score_computed: Mapped[float] = mapped_column(Float, default=35.0)
    pri_last_full_compute: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    total_inspections_approved: Mapped[int] = mapped_column(Integer, default=0)
    total_evidence_required: Mapped[int] = mapped_column(Integer, default=0)
    total_evidence_complete: Mapped[int] = mapped_column(Integer, default=0)
    total_disputes_caused: Mapped[int] = mapped_column(Integer, default=0)
    total_disputes_unresolved: Mapped[int] = mapped_column(Integer, default=0)
    total_supervised_count: Mapped[int] = mapped_column(Integer, default=0)
    supervised_avg_shi: Mapped[float] = mapped_column(Float, default=0.0)
    total_academy_completions: Mapped[int] = mapped_column(Integer, default=0)


class Project(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    uid: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    client: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    value: Mapped[float] = mapped_column(Float, default=0)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    phase: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active")
    progress: Mapped[float] = mapped_column(Float, default=0)
    shi: Mapped[float] = mapped_column(Float, default=0)
    started: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    target_completion: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    lead_engineer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("professionals.id"), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class ProjectAssignment(TimestampMixin, Base):
    __tablename__ = "project_assignments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_uid: Mapped[str] = mapped_column(String(100), index=True)
    professional_id: Mapped[int] = mapped_column(ForeignKey("professionals.id"), index=True)
    role_on_project: Mapped[str] = mapped_column(String(50), default="viewer")
    can_approve: Mapped[bool] = mapped_column(Boolean, default=False)


class PermissionGrant(TimestampMixin, Base):
    __tablename__ = "permission_grants"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    professional_id: Mapped[int] = mapped_column(ForeignKey("professionals.id"), index=True)
    resource_type: Mapped[str] = mapped_column(String(100), index=True)
    resource_uid: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    action: Mapped[str] = mapped_column(String(50), index=True)
    allowed: Mapped[bool] = mapped_column(Boolean, default=True)


class TwinStream(TimestampMixin, Base):
    __tablename__ = "twin_streams"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stream_key: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    project_uid: Mapped[str] = mapped_column(String(100), index=True)
    component_uid: Mapped[Optional[str]] = mapped_column(String(120), index=True, nullable=True)
    stream_type: Mapped[str] = mapped_column(String(50), default="project")


class TwinEvent(TimestampMixin, Base):
    __tablename__ = "twin_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stream_id: Mapped[int] = mapped_column(ForeignKey("twin_streams.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(120), index=True)
    aggregate_type: Mapped[str] = mapped_column(String(80), index=True)
    aggregate_uid: Mapped[str] = mapped_column(String(180), index=True)
    actor_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON)
    event_index: Mapped[int] = mapped_column(Integer, default=1)
    previous_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    current_hash: Mapped[str] = mapped_column(String(64), index=True)


class Component(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "components"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    uid: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    project_uid: Mapped[str] = mapped_column(String(100), index=True)
    type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    spec: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    grid: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    shi: Mapped[float] = mapped_column(Float, default=0)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    material_batch: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    executed_by: Mapped[Optional[int]] = mapped_column(ForeignKey("professionals.id"), nullable=True)
    approved_by: Mapped[Optional[int]] = mapped_column(ForeignKey("professionals.id"), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evidence_required: Mapped[bool] = mapped_column(Boolean, default=True)
    blocked_for_execution: Mapped[bool] = mapped_column(Boolean, default=True)


class ExecutionHold(TimestampMixin, Base):
    __tablename__ = "execution_holds"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    component_uid: Mapped[str] = mapped_column(String(120), index=True)
    project_uid: Mapped[str] = mapped_column(String(100), index=True)
    reason_code: Mapped[str] = mapped_column(String(100), default="EVIDENCE_REQUIRED")
    status: Mapped[str] = mapped_column(String(50), default="active")
    cleared_by: Mapped[Optional[int]] = mapped_column(ForeignKey("professionals.id"), nullable=True)
    detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class Evidence(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "evidence"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    component_uid: Mapped[str] = mapped_column(String(120), index=True)
    project_uid: Mapped[str] = mapped_column(String(100), index=True)
    type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    images: Mapped[int] = mapped_column(Integer, default=0)
    submitted_by: Mapped[Optional[int]] = mapped_column(ForeignKey("professionals.id"), nullable=True)
    approved_by: Mapped[Optional[int]] = mapped_column(ForeignKey("professionals.id"), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timestamp: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    geo: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    hash: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    manifest_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    # CAPTURE-LARGE fields (added by migration 0027)
    photo_type: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    geo_lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    geo_lon: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    geo_accuracy_m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    geo_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    capture_ts: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    server_ts: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    timestamp_drift_s: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    element_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    capture_large_package_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class EvidenceAsset(TimestampMixin, Base):
    __tablename__ = "evidence_assets"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    evidence_id: Mapped[int] = mapped_column(ForeignKey("evidence.id"), index=True)
    original_name: Mapped[str] = mapped_column(String(255))
    storage_path: Mapped[str] = mapped_column(String(500), unique=True)
    storage_backend: Mapped[str] = mapped_column(String(50), default="filesystem")
    content_type: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    size_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    immutable: Mapped[bool] = mapped_column(Boolean, default=True)


class SHIMethod(TimestampMixin, Base):
    __tablename__ = "shi_methods"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version_code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    material_weight: Mapped[float] = mapped_column(Float, default=0.3)
    assembly_weight: Mapped[float] = mapped_column(Float, default=0.4)
    environment_weight: Mapped[float] = mapped_column(Float, default=0.1)
    supervision_weight: Mapped[float] = mapped_column(Float, default=0.2)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Inspection(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "inspections"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    component_uid: Mapped[str] = mapped_column(String(120), index=True)
    project_uid: Mapped[str] = mapped_column(String(100), index=True)
    inspector_id: Mapped[Optional[int]] = mapped_column(ForeignKey("professionals.id"), nullable=True)
    method_id: Mapped[Optional[int]] = mapped_column(ForeignKey("shi_methods.id"), nullable=True)
    shi: Mapped[float] = mapped_column(Float, default=0)
    material_score: Mapped[float] = mapped_column(Float, default=0)
    assembly_score: Mapped[float] = mapped_column(Float, default=0)
    env_score: Mapped[float] = mapped_column(Float, default=0)
    supervision_score: Mapped[float] = mapped_column(Float, default=0)
    ai_flags: Mapped[int] = mapped_column(Integer, default=0)
    reason_tag: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timestamp: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    # SHI-2 sub-score fields (added by migration 0027)
    m_concrete_strength: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    m_steel_cert: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    m_batch_record: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    m_wc_ratio: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    m_curing_record: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    m_admixture: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    a_rebar_size: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    a_bar_spacing: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    a_cover: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    a_lap_length: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    a_tie_spacing: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    a_formwork: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    a_starter_bar: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    e_ambient_temp: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    e_humidity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    e_wind_sun: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    e_exposure_class: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    s_approver_band: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    s_evidence_completeness: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    s_reason_tag_quality: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    s_deviation_docs: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    penalty_concealed_deviation: Mapped[float] = mapped_column(Float, default=0.0)
    shi_material_total: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    shi_assembly_total: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    shi_env_total: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    shi_supervisory_total: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    inspector_pri_band: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    reason_tag_quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    construction_stage: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    min_shi_for_stage: Mapped[Optional[float]] = mapped_column(Float, nullable=True)


class Milestone(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "milestones"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_uid: Mapped[str] = mapped_column(String(100), index=True)
    name: Mapped[str] = mapped_column(String(255))
    phase: Mapped[int] = mapped_column(Integer, default=1)
    amount: Mapped[float] = mapped_column(Float, default=0)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    required_shi: Mapped[float] = mapped_column(Float, default=0)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    released_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class Payment(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "payments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_uid: Mapped[str] = mapped_column(String(100), index=True)
    milestone_id: Mapped[Optional[int]] = mapped_column(ForeignKey("milestones.id"), nullable=True)
    amount: Mapped[float] = mapped_column(Float, default=0)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    from_party: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    to_party: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    released_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    tx_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    gate_decision: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    gate_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class Tender(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "tenders"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    uid: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    client: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    value: Mapped[float] = mapped_column(Float, default=0)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    deadline: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="open")
    type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class Bid(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "bids"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tender_uid: Mapped[str] = mapped_column(String(100), index=True)
    firm: Mapped[str] = mapped_column(String(255))
    price: Mapped[float] = mapped_column(Float, default=0)
    integrity_score: Mapped[float] = mapped_column(Float, default=0)
    capacity_score: Mapped[float] = mapped_column(Float, default=0)
    shi_history: Mapped[float] = mapped_column(Float, default=0)
    matrix_score: Mapped[float] = mapped_column(Float, default=0)
    status: Mapped[str] = mapped_column(String(50), default="submitted")
    submitted_by: Mapped[Optional[int]] = mapped_column(ForeignKey("professionals.id"), nullable=True)


class Dispute(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "disputes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    uid: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    project_uid: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    component_uid: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    raised_by: Mapped[Optional[int]] = mapped_column(ForeignKey("professionals.id"), nullable=True)
    against_party: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="open")
    resolution: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raised_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    resolved_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    arbitrator_id: Mapped[Optional[int]] = mapped_column(ForeignKey("professionals.id"), nullable=True)
    determination_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)


class Material(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "materials"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_uid: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    grade: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    supplier: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    cert_number: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    projects_used: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    test_strength: Mapped[float] = mapped_column(Float, default=0)
    required_strength: Mapped[float] = mapped_column(Float, default=0)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    suspension_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class Certification(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "certifications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_uid: Mapped[str] = mapped_column(String(100), index=True)
    type: Mapped[str] = mapped_column(String(100))
    shi_composite: Mapped[float] = mapped_column(Float, default=0)
    issued_by: Mapped[Optional[int]] = mapped_column(ForeignKey("professionals.id"), nullable=True)
    co_signed_by: Mapped[Optional[int]] = mapped_column(ForeignKey("professionals.id"), nullable=True)
    issued_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    physical_plate: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    qr_code: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class AuditLog(TimestampMixin, Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    action: Mapped[str] = mapped_column(String(120), index=True)
    actor: Mapped[str] = mapped_column(String(255), index=True)
    detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timestamp: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    route: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    immutable: Mapped[bool] = mapped_column(Boolean, default=True)


class Sensor(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "sensors"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    component_uid: Mapped[str] = mapped_column(String(120), index=True)
    project_uid: Mapped[str] = mapped_column(String(100), index=True)
    type: Mapped[str] = mapped_column(String(100))
    current_reading: Mapped[float] = mapped_column(Float, default=0)
    unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    threshold: Mapped[float] = mapped_column(Float, default=0)
    status: Mapped[str] = mapped_column(String(50), default="normal")
    last_update: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)


class MonitorAlert(TimestampMixin, Base):
    __tablename__ = "monitor_alerts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sensor_id: Mapped[int] = mapped_column(ForeignKey("sensors.id"), index=True)
    project_uid: Mapped[str] = mapped_column(String(100), index=True)
    component_uid: Mapped[str] = mapped_column(String(120), index=True)
    reading: Mapped[float] = mapped_column(Float, default=0)
    threshold: Mapped[float] = mapped_column(Float, default=0)
    severity: Mapped[str] = mapped_column(String(50), default="medium")
    status: Mapped[str] = mapped_column(String(50), default="open")
    message: Mapped[str] = mapped_column(Text)


class Notification(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[str] = mapped_column(String(100))
    message: Mapped[str] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(50), default="medium")
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    for_role: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)


class RefreshToken(TimestampMixin, Base):
    __tablename__ = "refresh_tokens"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    professional_id: Mapped[int] = mapped_column(ForeignKey("professionals.id"), index=True)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AuthAttempt(TimestampMixin, Base):
    __tablename__ = "auth_attempts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), index=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    reason: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)


class EventLog(TimestampMixin, Base):
    __tablename__ = "event_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_type: Mapped[str] = mapped_column(String(120), index=True)
    payload: Mapped[dict] = mapped_column(JSON)


class AtlasSubscription(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "atlas_subscriptions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subscriber_name: Mapped[str] = mapped_column(String(255))
    subscriber_type: Mapped[str] = mapped_column(String(80), default="government")
    country_scope: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    access_tier: Mapped[str] = mapped_column(String(50), default="standard")
    status: Mapped[str] = mapped_column(String(50), default="active")


class AtlasReport(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "atlas_reports"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    country_scope: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    report_type: Mapped[str] = mapped_column(String(80), default="portfolio")
    period_label: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    generated_by: Mapped[Optional[int]] = mapped_column(ForeignKey("professionals.id"), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(50), default="published")


class FinancialProduct(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "financial_products"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(80), default="insurance")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    base_rate_bps: Mapped[float] = mapped_column(Float, default=0)
    min_shi: Mapped[float] = mapped_column(Float, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class UnderwritingApplication(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "underwriting_applications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_uid: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    project_uid: Mapped[str] = mapped_column(String(100), index=True)
    product_code: Mapped[str] = mapped_column(String(80), index=True)
    applicant_name: Mapped[str] = mapped_column(String(255))
    requested_amount: Mapped[float] = mapped_column(Float, default=0)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    status: Mapped[str] = mapped_column(String(50), default="submitted")
    submitted_by: Mapped[Optional[int]] = mapped_column(ForeignKey("professionals.id"), nullable=True)


class RiskDecision(TimestampMixin, Base):
    __tablename__ = "risk_decisions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("underwriting_applications.id"), index=True)
    risk_score: Mapped[float] = mapped_column(Float, default=0)
    decision: Mapped[str] = mapped_column(String(50), default="review")
    premium_adjustment_bps: Mapped[float] = mapped_column(Float, default=0)
    rationale: Mapped[str] = mapped_column(Text)
    feature_snapshot: Mapped[dict] = mapped_column(JSON)


class LearningPath(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "learning_paths"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    target_band: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    discipline_scope: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class Course(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "courses"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    path_code: Mapped[str] = mapped_column(String(80), index=True)
    code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    delivery_mode: Mapped[str] = mapped_column(String(50), default="async")
    hours: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(50), default="published")


class Enrollment(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "enrollments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    professional_id: Mapped[int] = mapped_column(ForeignKey("professionals.id"), index=True)
    course_code: Mapped[str] = mapped_column(String(80), index=True)
    path_code: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="enrolled")
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class CredentialAward(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "credential_awards"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    professional_id: Mapped[int] = mapped_column(ForeignKey("professionals.id"), index=True)
    path_code: Mapped[str] = mapped_column(String(80), index=True)
    credential_title: Mapped[str] = mapped_column(String(255))
    awarded_by: Mapped[Optional[int]] = mapped_column(ForeignKey("professionals.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="awarded")
    advancement_recommended: Mapped[bool] = mapped_column(Boolean, default=False)


class Country(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "countries"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(8), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    region: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    launch_stage: Mapped[str] = mapped_column(String(50), default="pipeline")
    readiness_score: Mapped[float] = mapped_column(Float, default=0)
    regulator_appetite: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active")


class CountryTenant(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "country_tenants"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    country_code: Mapped[str] = mapped_column(String(8), index=True)
    operator_name: Mapped[str] = mapped_column(String(255))
    license_type: Mapped[str] = mapped_column(String(80), default="country_franchise")
    revenue_share_pct: Mapped[float] = mapped_column(Float, default=0)
    launch_status: Mapped[str] = mapped_column(String(50), default="pending")
    start_date: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    end_date: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)


class LaunchProgram(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "launch_programs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    country_code: Mapped[str] = mapped_column(String(8), index=True)
    title: Mapped[str] = mapped_column(String(255))
    phase: Mapped[str] = mapped_column(String(80), default="readiness")
    progress: Mapped[float] = mapped_column(Float, default=0)
    owner_professional_id: Mapped[Optional[int]] = mapped_column(ForeignKey("professionals.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class RevenueShareRule(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "revenue_share_rules"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    country_code: Mapped[str] = mapped_column(String(8), index=True)
    module_code: Mapped[str] = mapped_column(String(80))
    local_operator_pct: Mapped[float] = mapped_column(Float, default=0)
    central_platform_pct: Mapped[float] = mapped_column(Float, default=0)
    government_program_pct: Mapped[float] = mapped_column(Float, default=0)
    status: Mapped[str] = mapped_column(String(50), default="active")


class CSTMember(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "cst_members"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    professional_id: Mapped[int] = mapped_column(ForeignKey("professionals.id"), index=True)
    appointment_title: Mapped[str] = mapped_column(String(120), default="Council Member")
    voting_rights: Mapped[bool] = mapped_column(Boolean, default=True)
    term_start: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    term_end: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active")


class GovernanceCommittee(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "governance_committees"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    scope: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active")


class GovernanceResolution(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "governance_resolutions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    resolution_uid: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    committee_code: Mapped[str] = mapped_column(String(50), index=True)
    title: Mapped[str] = mapped_column(String(255))
    resolution_type: Mapped[str] = mapped_column(String(80), default="standard")
    body_text: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default="draft")
    effective_date: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    issued_by: Mapped[Optional[int]] = mapped_column(ForeignKey("professionals.id"), nullable=True)


class GovernanceVote(TimestampMixin, Base):
    __tablename__ = "governance_votes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    resolution_uid: Mapped[str] = mapped_column(String(100), index=True)
    member_professional_id: Mapped[int] = mapped_column(ForeignKey("professionals.id"), index=True)
    vote: Mapped[str] = mapped_column(String(20), default="yes")
    rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class AuthorityDelegation(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "authority_delegations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    authority_code: Mapped[str] = mapped_column(String(80), index=True)
    delegate_professional_id: Mapped[int] = mapped_column(ForeignKey("professionals.id"), index=True)
    scope: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default="active")
    valid_until: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)


class Regulation(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "regulations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    country_code: Mapped[str] = mapped_column(String(8), index=True)
    regulation_code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(80), default="construction_integrity")
    status: Mapped[str] = mapped_column(String(50), default="draft")
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class Consultation(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "consultations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    consultation_uid: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    country_code: Mapped[str] = mapped_column(String(8), index=True)
    title: Mapped[str] = mapped_column(String(255))
    consultation_type: Mapped[str] = mapped_column(String(80), default="regulatory")
    status: Mapped[str] = mapped_column(String(50), default="open")
    opened_at_label: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    closed_at_label: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)


class ComplianceMapping(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "compliance_mappings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    country_code: Mapped[str] = mapped_column(String(8), index=True)
    standard_code: Mapped[str] = mapped_column(String(80), index=True)
    module_code: Mapped[str] = mapped_column(String(80), index=True)
    requirement_summary: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default="mapped")
