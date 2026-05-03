"""
VERITAS INFRA™ — PREFAB™ Router
API endpoints for component specification, deviation management,
deviation log closure, and SEAL™ Gate 9 verification.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import require_action
from app.db.session import get_db
from app.models.entities import Professional
from app.models.prefab import PrefabLibraryEntry
from app.schemas.prefab import (
    ComponentSpecApprove, ComponentSpecCreate, ComponentSpecOut,
    ComponentSpecSummary, DeviationCorrect, DeviationCreate,
    DeviationLogCloseRequest, DeviationOut, DeviationReview,
    LibraryEntryCreate, LibraryEntryOut, PrefabSealCheck,
)
from app.services.audit import record_audit
from app.services.prefab import (
    ComponentSpecService, DeviationService,
    PrefabLibraryService, PrefabSealGateService,
)

router = APIRouter(prefix="/prefab", tags=["PREFAB™ — Specification Spine"])


# ══════════════════════════════════════════════════════════════
# SPECIFICATION LIBRARY
# ══════════════════════════════════════════════════════════════

@router.get("/library", summary="List specification library entries")
def list_library(
    component_type: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: Professional = Depends(require_action("prefab:read")),
):
    """
    Browse the specification library. Reusable templates created by
    TRUSTED+ engineers for common structural elements.
    """
    items, total = PrefabLibraryService.list_entries(db, component_type, skip, limit)
    return {
        "items": [LibraryEntryOut.model_validate(i).model_dump() for i in items],
        "total": total,
    }


@router.post("/library", response_model=LibraryEntryOut, status_code=201,
             summary="Create a reusable specification template")
def create_library_entry(
    payload: LibraryEntryCreate,
    db: Session = Depends(get_db),
    current_user: Professional = Depends(require_action("prefab:write")),
):
    """
    Create a reusable specification template.
    Requires TRUSTED PRI band or higher.
    """
    return PrefabLibraryService.create_entry(
        db, payload.model_dump(exclude_none=True), current_user
    )


# ══════════════════════════════════════════════════════════════
# COMPONENT SPECIFICATIONS
# ══════════════════════════════════════════════════════════════

@router.post("/specs", response_model=ComponentSpecOut, status_code=201,
             summary="Create a component specification")
def create_spec(
    payload: ComponentSpecCreate,
    db: Session = Depends(get_db),
    current_user: Professional = Depends(require_action("prefab:write")),
):
    """
    Create a structural specification for a component UID.

    The specification is the source of truth for BUILD™ evidence checks,
    VISION™ inspection scoring, and SEAL™ Gate 9 verification.

    HIGH and CRITICAL sensitivity specs require the creating engineer
    to hold PRI: TRUSTED or HONOR.
    """
    try:
        spec = ComponentSpecService.create_spec(db, payload, current_user)
        return ComponentSpecOut.model_validate(spec)
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/specs/project/{project_uid}",
            summary="List all component specs for a project")
def list_project_specs(
    project_uid: str,
    sensitivity: str | None = Query(None),
    approved_only: bool = Query(False),
    has_open_deviations: bool | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: Professional = Depends(require_action("prefab:read")),
):
    items, total = ComponentSpecService.list_project_specs(
        db, project_uid, sensitivity, approved_only, has_open_deviations, skip, limit
    )
    return {
        "items": [ComponentSpecSummary.model_validate(i).model_dump() for i in items],
        "total": total,
    }


@router.get("/specs/uid/{component_uid}", response_model=ComponentSpecOut,
            summary="Get spec by component UID")
def get_spec_by_uid(
    component_uid: str,
    db: Session = Depends(get_db),
    current_user: Professional = Depends(require_action("prefab:read")),
):
    """Retrieve the full specification for a component UID."""
    spec = ComponentSpecService.get_spec_by_uid(db, component_uid)
    if not spec:
        raise HTTPException(
            status_code=404,
            detail=f"No specification found for UID '{component_uid}'. "
                   "A TRUSTED+ engineer must create the spec before construction begins."
        )
    return ComponentSpecOut.model_validate(spec)


@router.post("/specs/{spec_id}/approve", response_model=ComponentSpecOut,
             summary="Approve a component specification")
def approve_spec(
    spec_id: int,
    payload: ComponentSpecApprove,
    db: Session = Depends(get_db),
    current_user: Professional = Depends(require_action("prefab:approve")),
):
    """
    Approve a component specification.

    The approver's PRI band must meet the minimum for the spec's
    execution sensitivity level:
    - LOW / MEDIUM → STABLE or above
    - HIGH / CRITICAL → TRUSTED or above
    """
    try:
        spec = ComponentSpecService.approve_spec(
            db, spec_id, current_user, payload.approval_notes
        )
        return ComponentSpecOut.model_validate(spec)
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=422, detail=str(e))


# ══════════════════════════════════════════════════════════════
# DEVIATION RECORDS
# ══════════════════════════════════════════════════════════════

@router.post("/deviations", response_model=DeviationOut, status_code=201,
             summary="Report a structural deviation")
def report_deviation(
    payload: DeviationCreate,
    db: Session = Depends(get_db),
    current_user: Professional = Depends(require_action("prefab:write")),
):
    """
    Report a deviation from the approved ComponentSpec.

    MAJOR and CRITICAL deviations require before_photo_url and after_photo_url
    (CAPTURE-LARGE Element 4 — Before/After Correction Pair).

    CRITICAL deviations automatically trigger:
    - PAY™ hold on all pending milestones
    - TWIN™ event with PAY hold notification
    - Ethics violation flag for review
    """
    try:
        record = DeviationService.report_deviation(db, payload, current_user)
        return DeviationOut.model_validate(record)
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/deviations/project/{project_uid}",
            summary="List all deviation records for a project")
def list_project_deviations(
    project_uid: str,
    closed: bool | None = Query(None),
    severity: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: Professional = Depends(require_action("prefab:read")),
):
    from app.models.prefab import DeviationRecord
    q = db.query(DeviationRecord).filter(
        DeviationRecord.project_uid == project_uid
    )
    if closed is not None:
        q = q.filter(DeviationRecord.closed.is_(closed))
    if severity:
        q = q.filter(DeviationRecord.severity == severity.upper())
    total = q.count()
    items = q.order_by(DeviationRecord.id.desc()).offset(skip).limit(limit).all()
    return {
        "items": [DeviationOut.model_validate(i).model_dump() for i in items],
        "total": total,
    }


@router.post("/deviations/{deviation_id}/correct", response_model=DeviationOut,
             summary="Record correction of a deviation")
def mark_corrected(
    deviation_id: int,
    payload: DeviationCorrect,
    db: Session = Depends(get_db),
    current_user: Professional = Depends(require_action("prefab:write")),
):
    """
    Record that a deviation has been corrected.
    Must supply the after-photo confirming correction.
    MINOR deviations auto-close. MAJOR/CRITICAL require engineer review.
    """
    try:
        record = DeviationService.mark_corrected(db, deviation_id, payload, current_user)
        return DeviationOut.model_validate(record)
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/deviations/{deviation_id}/review", response_model=DeviationOut,
             summary="Engineer review of a MAJOR or CRITICAL deviation")
def review_deviation(
    deviation_id: int,
    payload: DeviationReview,
    db: Session = Depends(get_db),
    current_user: Professional = Depends(require_action("prefab:approve")),
):
    """
    MAJOR/CRITICAL deviation engineer review.
    - MAJOR: requires PRI: TRUSTED or HONOR
    - CRITICAL: requires PRI: HONOR

    Accepted → deviation closes. Rejected → remains open.
    Requires_remediation → remediation plan must be submitted before close.
    """
    try:
        record = DeviationService.review_deviation(db, deviation_id, payload, current_user)
        return DeviationOut.model_validate(record)
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=422, detail=str(e))


# ══════════════════════════════════════════════════════════════
# DEVIATION LOG CLOSURE — SEAL™ GATE 9
# ══════════════════════════════════════════════════════════════

@router.post("/specs/{spec_id}/close-deviation-log",
             response_model=ComponentSpecOut,
             summary="Close the deviation log (SEAL™ Gate 9)")
def close_deviation_log(
    spec_id: int,
    payload: DeviationLogCloseRequest,
    db: Session = Depends(get_db),
    current_user: Professional = Depends(require_action("prefab:approve")),
):
    """
    Formally close the deviation log for a component specification.

    This is SEAL™ Gate 9. All deviations must be individually resolved
    before this endpoint will succeed. HIGH/CRITICAL components require
    a TRUSTED+ engineer to close.

    This must be completed for EVERY component in a project before the
    SEAL™ certificate can be issued.
    """
    try:
        spec = DeviationService.close_deviation_log(db, spec_id, payload, current_user)
        return ComponentSpecOut.model_validate(spec)
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=422, detail=str(e))


# ══════════════════════════════════════════════════════════════
# SEAL™ GATE 9 CHECK
# ══════════════════════════════════════════════════════════════

@router.get("/seal-gate/{project_uid}", response_model=PrefabSealCheck,
            summary="Check PREFAB™ readiness for SEAL™ issuance (Gate 9)")
def check_seal_gate(
    project_uid: str,
    db: Session = Depends(get_db),
    current_user: Professional = Depends(require_action("prefab:read")),
):
    """
    SEAL™ Gate 9 check: Are all PREFAB™ conditions met for certification?

    Returns a full analysis of:
    - Component specs created vs total components
    - Approved specs count
    - Deviation logs closed
    - Open deviations remaining

    gate_passed: true = Gate 9 cleared. false = Reasons for failure listed.
    """
    return PrefabSealGateService.check_seal_gate(db, project_uid)


# ══════════════════════════════════════════════════════════════
# UID GENERATOR UTILITY
# ══════════════════════════════════════════════════════════════

@router.get("/uid/generate", summary="Generate a canonical component UID")
def generate_component_uid(
    project_code: str = Query(..., description="e.g. BLD-IKEJA"),
    level: str = Query(..., description="e.g. L3"),
    grid: str = Query(..., description="e.g. C4"),
    component_type: str = Query(..., description="e.g. COL"),
    sequence: int = Query(..., ge=1, le=99999),
    current_user: Professional = Depends(require_action("prefab:read")),
):
    """
    Generate a canonical PREFAB™ Component UID.
    Output format: PROJECT_CODE/LEVEL/GRID/TYPE/SEQ
    Example: BLD-IKEJA/L3/C4/COL/019
    """
    from app.models.prefab import generate_uid, validate_uid_format
    uid = generate_uid(project_code, level, grid, component_type, sequence)
    return {
        "uid": uid,
        "format_valid": validate_uid_format(uid),
        "parsed": {
            "project_code": project_code.upper(),
            "level": level.upper(),
            "grid": grid.upper(),
            "type": component_type.upper(),
            "sequence": f"{sequence:03d}",
        },
    }


@router.get("/uid/validate/{uid:path}", summary="Validate a component UID format")
def validate_uid(
    uid: str,
    current_user: Professional = Depends(require_action("prefab:read")),
):
    """Check whether a UID string conforms to the canonical PREFAB™ format."""
    from app.models.prefab import validate_uid_format, parse_uid
    valid = validate_uid_format(uid)
    return {
        "uid": uid,
        "valid": valid,
        "parsed": parse_uid(uid) if valid else None,
        "expected_format": "PROJECT_CODE/LEVEL/GRID/TYPE/SEQUENCE — e.g. BLD-IKEJA/L3/C4/COL/019",
    }
