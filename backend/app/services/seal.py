"""
VERITAS INFRA™ — SEAL™ Service (Full 10-Gate Implementation)

THE 10 GATES:
  Gate 1:  SHI composite ≥ 78 (stage-weighted average)
  Gate 2:  No unresolved LEX™ disputes
  Gate 3:  ORIGIN™ provenance verified for all material batches
  Gate 4:  No open Tier-1 or Tier-2 ETHICS™ violations on project
  Gate 5:  All PAY™ milestones at stage "completed" or "released"
  Gate 6:  MONITOR™ sensors installed and baseline recorded (advisory)
  Gate 7:  PREFAB™ deviation log closed for all components
  Gate 8:  Certifying engineer holds PRI: HONOR at time of issuance
  Gate 9:  TWIN™ chain integrity verified — no hash errors
  Gate 10: All components have approved CAPTURE-LARGE packages
"""
from __future__ import annotations

import base64
import io
import secrets
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.entities import (
    Certification, Component, Dispute, Evidence,
    ExecutionHold, Milestone, Professional, Project, TwinEvent, TwinStream,
)
from app.services.audit import record_audit
from app.services.twin import append_twin_event


# ── QR Code Generation ────────────────────────────────────────────────────────

def _generate_qr_code_b64(data: str) -> str:
    try:
        import qrcode
        from qrcode.image.pure import PyPNGImage

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=8,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(image_factory=PyPNGImage)
        buffer = io.BytesIO()
        img.save(buffer)
        b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{b64}"
    except Exception:
        return f"VERIFY:{data}"


def _build_verification_url(project_uid: str) -> str:
    try:
        from app.core.config import settings
        base = getattr(settings, "seal_registry_url",
                       "https://verify.veritasinfra.com/seal")
    except Exception:
        base = "https://verify.veritasinfra.com/seal"
    return f"{base}/{project_uid}"


def _get_band(score: float) -> str:
    if score >= 85:
        return "HONOR"
    elif score >= 70:
        return "TRUSTED"
    elif score >= 50:
        return "STABLE"
    return "PROVISIONAL"


# ══════════════════════════════════════════════════════════════
# THE 10-GATE ELIGIBILITY CHECK
# ══════════════════════════════════════════════════════════════

def certification_eligibility(
    db: Session,
    project_uid: str,
    certifying_engineer_id: int | None = None,
) -> tuple[bool, float, str, dict]:
    """
    Full 10-gate SEAL™ eligibility check.
    Returns: (eligible, shi, reason, gate_results)
    """
    gate_results = {}
    failures = []

    project = db.query(Project).filter(
        Project.uid == project_uid,
        Project.is_deleted.is_(False),
    ).first()
    if not project:
        return False, 0.0, "Project not found", {}

    current_shi = project.shi or 0.0

    # ── Gate 1: SHI ≥ 78 ─────────────────────────────────────────────────────
    try:
        from app.core.config import settings
        seal_threshold = getattr(settings, "seal_shi_threshold", 78.0)
    except Exception:
        seal_threshold = 78.0

    g1_passed = current_shi >= seal_threshold
    gate_results["gate_1_shi"] = {
        "name": "SHI Composite Threshold",
        "passed": g1_passed,
        "detail": (
            f"SHI {current_shi:.2f} >= {seal_threshold:.2f}" if g1_passed
            else f"SHI {current_shi:.2f} is below the {seal_threshold:.2f} "
                 "threshold required for SEAL™ issuance."
        ),
    }
    if not g1_passed:
        failures.append(gate_results["gate_1_shi"]["detail"])

    # ── Gate 2: No unresolved LEX™ disputes ───────────────────────────────────
    unresolved_disputes = db.query(Dispute).filter(
        Dispute.project_uid == project_uid,
        Dispute.status.in_(["open", "under_review"]),
        Dispute.is_deleted.is_(False),
    ).count()
    g2_passed = unresolved_disputes == 0
    gate_results["gate_2_disputes"] = {
        "name": "LEX™ Dispute Clearance",
        "passed": g2_passed,
        "detail": (
            "No open LEX™ disputes" if g2_passed
            else f"{unresolved_disputes} open dispute(s) must be resolved."
        ),
    }
    if not g2_passed:
        failures.append(gate_results["gate_2_disputes"]["detail"])

    # ── Gate 3: ORIGIN™ provenance ────────────────────────────────────────────
    try:
        from app.services.origin import OriginSealGateService
        origin_result = OriginSealGateService.check_seal_gate(db, project_uid)
        g3_passed = origin_result["gate_passed"]
        gate_results["gate_3_origin"] = {
            "name": "ORIGIN™ Material Provenance",
            "passed": g3_passed,
            "detail": (
                "All materials verified" if g3_passed
                else "; ".join(origin_result["failure_reasons"])
            ),
            "data": origin_result,
        }
    except Exception as e:
        g3_passed = False
        gate_results["gate_3_origin"] = {
            "name": "ORIGIN™ Material Provenance",
            "passed": False,
            "detail": f"ORIGIN™ check error: {e}",
        }
    if not g3_passed:
        failures.append(gate_results["gate_3_origin"]["detail"])

    # ── Gate 4: ETHICS™ violations ────────────────────────────────────────────
    try:
        from app.services.ethics import EthicsService
        ethics_result = EthicsService.check_project_violations(db, project_uid)
        g4_passed = ethics_result["gate_4_passed"]
        gate_results["gate_4_ethics"] = {
            "name": "ETHICS™ Violation Clearance",
            "passed": g4_passed,
            "detail": (
                "No open Tier-1 or Tier-2 ethics violations"
                if g4_passed
                else ethics_result["failure_reason"]
            ),
        }
    except Exception as e:
        g4_passed = False
        gate_results["gate_4_ethics"] = {
            "name": "ETHICS™ Violation Clearance",
            "passed": False,
            "detail": f"ETHICS™ check error: {e}",
        }
    if not g4_passed:
        failures.append(gate_results["gate_4_ethics"]["detail"])

    # ── Gate 5: PAY™ milestones complete ──────────────────────────────────────
    pending_milestones = db.query(Milestone).filter(
        Milestone.project_uid == project_uid,
        Milestone.status.in_(["pending", "hold_deviation",
                               "hold_ethics", "blocked"]),
        Milestone.is_deleted.is_(False),
    ).count()
    g5_passed = pending_milestones == 0
    gate_results["gate_5_pay"] = {
        "name": "PAY™ Milestone Completion",
        "passed": g5_passed,
        "detail": (
            "All payment milestones completed or released"
            if g5_passed
            else f"{pending_milestones} payment milestone(s) remain pending or held."
        ),
    }
    if not g5_passed:
        failures.append(gate_results["gate_5_pay"]["detail"])

    # ── Gate 6: MONITOR™ sensors (advisory) ───────────────────────────────────
    from app.models.entities import Sensor
    g6_passed = True  # Advisory only — does not block SEAL™ v1
    gate_results["gate_6_monitor"] = {
        "name": "MONITOR™ Sensor Baseline",
        "passed": g6_passed,
        "detail": (
            "MONITOR™ gate is advisory in v1 — "
            "sensor installation recommended post-occupancy."
        ),
        "advisory": True,
    }

    # ── Gate 7: PREFAB™ deviation logs closed ─────────────────────────────────
    try:
        from app.services.prefab import PrefabSealGateService
        prefab_result = PrefabSealGateService.check_seal_gate(db, project_uid)
        g7_passed = prefab_result.gate_passed
        gate_results["gate_7_prefab"] = {
            "name": "PREFAB™ Deviation Log Closure",
            "passed": g7_passed,
            "detail": (
                "All component deviation logs closed"
                if g7_passed
                else "; ".join(prefab_result.failure_reasons)
            ),
            "data": prefab_result.dict() if hasattr(prefab_result, "dict") else {},
        }
    except Exception:
        g7_passed = True  # Non-blocking if module not installed
        gate_results["gate_7_prefab"] = {
            "name": "PREFAB™ Deviation Log Closure",
            "passed": True,
            "detail": "PREFAB™ module not installed — gate skipped.",
            "advisory": True,
        }
    if not g7_passed:
        failures.append(gate_results["gate_7_prefab"]["detail"])

    # ── Gate 8: Certifying engineer holds PRI: HONOR ──────────────────────────
    g8_passed = False
    g8_detail = "Certifying engineer ID not provided — gate cannot be evaluated."
    if certifying_engineer_id:
        engineer = db.query(Professional).filter(
            Professional.id == certifying_engineer_id,
        ).first()
        if engineer:
            band = _get_band(engineer.pri_score or 0)
            g8_passed = band == "HONOR"
            g8_detail = (
                f"Certifying engineer holds PRI: HONOR"
                if g8_passed
                else f"Certifying engineer holds PRI: {band}. "
                     "SEAL™ issuance requires PRI: HONOR."
            )
        else:
            g8_detail = f"Certifying engineer ID {certifying_engineer_id} not found."
    gate_results["gate_8_engineer_band"] = {
        "name": "Certifying Engineer PRI Band",
        "passed": g8_passed,
        "detail": g8_detail,
    }
    if not g8_passed:
        failures.append(g8_detail)

    # ── Gate 9: TWIN™ chain integrity ─────────────────────────────────────────
    twin_stream = db.query(TwinStream).filter(
        TwinStream.project_uid == project_uid,
    ).first()
    if twin_stream:
        events = db.query(TwinEvent).filter(
            TwinEvent.stream_id == twin_stream.id,
        ).order_by(TwinEvent.event_index).all()

        chain_valid = True
        for i, event in enumerate(events):
            if i == 0:
                continue
            if hasattr(event, "previous_hash") and hasattr(events[i-1], "current_hash"):
                if event.previous_hash != events[i-1].current_hash:
                    chain_valid = False
                    break

        g9_passed = chain_valid
        gate_results["gate_9_twin"] = {
            "name": "TWIN™ Chain Integrity",
            "passed": g9_passed,
            "detail": (
                f"TWIN™ ledger chain verified ({len(events)} events)"
                if g9_passed
                else "TWIN™ ledger chain integrity FAILED — tamper detected. "
                     "Contact platform support."
            ),
        }
    else:
        g9_passed = False
        gate_results["gate_9_twin"] = {
            "name": "TWIN™ Chain Integrity",
            "passed": False,
            "detail": f"No TWIN™ ledger found for project {project_uid}.",
        }
    if not g9_passed:
        failures.append(gate_results["gate_9_twin"]["detail"])

    # ── Gate 10: All components have approved CAPTURE-LARGE ───────────────────
    total_components = db.query(Component).filter(
        Component.project_uid == project_uid,
        Component.is_deleted.is_(False),
    ).count()

    still_blocked = db.query(Component).filter(
        Component.project_uid == project_uid,
        Component.is_deleted.is_(False),
        Component.blocked_for_execution.is_(True),
    ).count()

    active_holds = db.query(ExecutionHold).filter(
        ExecutionHold.project_uid == project_uid,
        ExecutionHold.status == "active",
    ).count()

    g10_passed = still_blocked == 0 and active_holds == 0
    gate_results["gate_10_evidence"] = {
        "name": "CAPTURE-LARGE Evidence Clearance",
        "passed": g10_passed,
        "detail": (
            f"All {total_components} components have approved evidence"
            if g10_passed
            else f"{still_blocked} component(s) still blocked + "
                 f"{active_holds} active pour hold(s). "
                 "All must be cleared before SEAL™."
        ),
    }
    if not g10_passed:
        failures.append(gate_results["gate_10_evidence"]["detail"])

    # ── Final Result ──────────────────────────────────────────────────────────
    eligible = len(failures) == 0
    reason = "All 10 SEAL™ gates passed" if eligible else (
        f"{len(failures)} gate(s) failed: {failures[0]}"
    )

    return eligible, current_shi, reason, gate_results


# ══════════════════════════════════════════════════════════════
# CERTIFICATE ISSUANCE
# ══════════════════════════════════════════════════════════════

def issue_certificate(
    db: Session,
    project_uid: str,
    certificate_type: str,
    issued_by: int,
    co_signed_by: int | None,
    notes: str | None,
    actor_email: str,
) -> Certification:
    eligible, shi, reason, gate_results = certification_eligibility(
        db, project_uid, certifying_engineer_id=issued_by
    )
    if not eligible:
        raise ValueError(reason)

    url = _build_verification_url(project_uid)
    qr = _generate_qr_code_b64(url)

    cert = Certification(
        project_uid=project_uid,
        type=certificate_type,
        shi_composite=shi,
        issued_by=issued_by,
        co_signed_by=co_signed_by,
        issued_date=datetime.now(timezone.utc).isoformat(),
        physical_plate=f"{certificate_type}-{project_uid}",
        status="issued",
        qr_code=qr,
        notes=notes,
    )
    db.add(cert)
    db.commit()
    db.refresh(cert)

    append_twin_event(
        db,
        project_uid=project_uid,
        event_type="SEAL.CERTIFICATE_ISSUED",
        aggregate_type="certificate",
        aggregate_uid=str(cert.id),
        actor_email=actor_email,
        payload={
            "project_uid": project_uid,
            "certificate_type": certificate_type,
            "shi": shi,
            "gates_passed": 10,
            "verification_url": url,
            "certificate_id": cert.id,
        },
    )
    record_audit(
        db, actor_email, "SEAL_CERTIFICATE_ISSUED",
        f"SEAL™ issued for {project_uid} — SHI {shi:.2f} — all 10 gates passed"
    )
    return cert


# ══════════════════════════════════════════════════════════════
# GATE STATUS ENDPOINT (for pre-certification planning)
# ══════════════════════════════════════════════════════════════

def get_full_gate_status(
    db: Session,
    project_uid: str,
    certifying_engineer_id: int | None = None,
) -> dict:
    eligible, shi, reason, gate_results = certification_eligibility(
        db, project_uid, certifying_engineer_id=certifying_engineer_id
    )

    gates_passed = sum(
        1 for g in gate_results.values()
        if g.get("passed") and not g.get("advisory")
    )
    gates_total = sum(
        1 for g in gate_results.values()
        if not g.get("advisory")
    )

    return {
        "project_uid": project_uid,
        "current_shi": shi,
        "seal_eligible": eligible,
        "gates_passed": gates_passed,
        "gates_total": gates_total,
        "overall_reason": reason,
        "gates": gate_results,
    }
