"""
VERITAS INFRA™ — ORIGIN™ Module Models
Complete material provenance and supply chain verification.

SEAL™ Gate 3 requires ALL materials on a project to have
verified ORIGIN™ provenance records.

New tables: origin_suppliers, origin_material_batches,
            origin_supply_chain_records, origin_test_records.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey,
    Index, Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SupplierTier(str, PyEnum):
    UNVERIFIED  = "unverified"
    PROVISIONAL = "provisional"
    APPROVED    = "approved"
    SUSPENDED   = "suspended"
    BLACKLISTED = "blacklisted"


class MaterialType(str, PyEnum):
    REINFORCING_STEEL   = "reinforcing_steel"
    STRUCTURAL_STEEL    = "structural_steel"
    READY_MIX_CONCRETE  = "ready_mix_concrete"
    CEMENT              = "cement"
    AGGREGATE_COARSE    = "aggregate_coarse"
    AGGREGATE_FINE      = "aggregate_fine"
    ADMIXTURE           = "admixture"
    PRESTRESSING_STRAND = "prestressing_strand"
    STRUCTURAL_TIMBER   = "structural_timber"
    MASONRY_BLOCK       = "masonry_block"
    OTHER               = "other"


class TestStandard(str, PyEnum):
    BS_4449    = "BS_4449"
    ASTM_A615  = "ASTM_A615"
    EN_10080   = "EN_10080"
    BS_8500    = "BS_8500"
    ASTM_C94   = "ASTM_C94"
    EN_206     = "EN_206"
    NIS        = "NIS"
    ISO_6935   = "ISO_6935"
    OTHER      = "OTHER"


class ProvenanceStatus(str, PyEnum):
    INCOMPLETE  = "incomplete"
    PENDING     = "pending"
    VERIFIED    = "verified"
    DISPUTED    = "disputed"
    REJECTED    = "rejected"


# ── Origin Supplier ───────────────────────────────────────────────────────────

class OriginSupplier(Base):
    __tablename__ = "origin_suppliers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    uid: Mapped[str] = mapped_column(
        String(80), unique=True, index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    country: Mapped[str] = mapped_column(String(100), nullable=False)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    registration_number: Mapped[Optional[str]] = mapped_column(
        String(120), nullable=True
    )
    material_types: Mapped[list] = mapped_column(JSON, default=list)

    tier: Mapped[str] = mapped_column(
        String(20), default=SupplierTier.UNVERIFIED, nullable=False
    )
    tier_last_assessed: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    suspension_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    audit_report_url: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True
    )
    audit_expiry: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    total_batches_registered: Mapped[int] = mapped_column(Integer, default=0)
    batches_verified: Mapped[int] = mapped_column(Integer, default=0)
    batches_rejected: Mapped[int] = mapped_column(Integer, default=0)
    avg_strength_ratio: Mapped[float] = mapped_column(Float, default=0.0)

    __table_args__ = (
        Index("ix_origin_suppliers_tier", "tier"),
        Index("ix_origin_suppliers_country", "country"),
    )


# ── Origin Material Batch ─────────────────────────────────────────────────────

class OriginMaterialBatch(Base):
    """
    A specific batch of material from a specific supplier.
    The batch_uid links to Material.batch_uid in the existing table.
    """
    __tablename__ = "origin_material_batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    batch_uid: Mapped[str] = mapped_column(
        String(120), unique=True, index=True, nullable=False
    )
    material_type: Mapped[str] = mapped_column(String(50), nullable=False)

    supplier_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("origin_suppliers.id"), nullable=True, index=True
    )
    supplier_uid: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    production_plant: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    production_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    heat_number: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    mix_design_ref: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)

    specified_grade: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    specified_strength_mpa: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    design_standard: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)

    delivery_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    delivery_note_number: Mapped[Optional[str]] = mapped_column(
        String(120), nullable=True
    )
    delivery_note_url: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True
    )
    quantity_delivered: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    quantity_unit: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    projects_used: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    components_used: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    mill_cert_number: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    mill_cert_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    mill_cert_sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    provenance_status: Mapped[str] = mapped_column(
        String(20), default=ProvenanceStatus.INCOMPLETE, nullable=False, index=True
    )
    verified_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("professionals.id"), nullable=True
    )
    verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    verification_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    strength_ratio: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    anomaly_flags: Mapped[list] = mapped_column(JSON, default=list)
    ethics_flag_triggered: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (
        Index("ix_origin_batches_supplier", "supplier_id", "provenance_status"),
        Index("ix_origin_batches_status", "provenance_status"),
    )


# ── Supply Chain Record ───────────────────────────────────────────────────────

class OriginSupplyChainRecord(Base):
    __tablename__ = "origin_supply_chain_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    batch_uid: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    batch_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("origin_material_batches.id"), nullable=True
    )

    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    step_type: Mapped[str] = mapped_column(String(50), nullable=False)

    from_party: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    to_party: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    from_location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    to_location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    from_geo: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    to_geo: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)

    transfer_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    quantity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    quantity_unit: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    document_ref: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    document_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    document_sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    recorded_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("professionals.id"), nullable=True
    )
    verified: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (
        Index("ix_origin_chain_batch", "batch_uid", "step_number"),
    )


# ── Test Record ───────────────────────────────────────────────────────────────

class OriginTestRecord(Base):
    __tablename__ = "origin_test_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    batch_uid: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    batch_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("origin_material_batches.id"), nullable=True
    )

    test_standard: Mapped[str] = mapped_column(String(30), nullable=False)
    laboratory_name: Mapped[str] = mapped_column(String(255), nullable=False)
    laboratory_accreditation: Mapped[Optional[str]] = mapped_column(
        String(120), nullable=True
    )

    test_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sample_reference: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)

    specified_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    actual_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    unit: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    test_type: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    passed: Mapped[bool] = mapped_column(Boolean, default=False)
    strength_ratio: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    certificate_number: Mapped[Optional[str]] = mapped_column(
        String(120), nullable=True
    )
    certificate_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    certificate_sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    verified_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("professionals.id"), nullable=True
    )
    verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    anomaly_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    anomaly_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_origin_tests_batch", "batch_uid"),
    )
