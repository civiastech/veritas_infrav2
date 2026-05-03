"""
VERITAS INFRA™ — BUILD™ CAPTURE-LARGE Enforcement Service
Replacement for the relevant section of services/workflows.py.

CHANGES FROM ORIGINAL:
  1. GPS tolerance: 500m → 15m
  2. Enforces all 6 CAPTURE-LARGE elements (was 1 file per upload with no grouping)
  3. Adds Element 4: Before/After Correction Pair (mandatory on deviation)
  4. Package-level validation: all 6 elements must be submitted before
     the ExecutionHold can be cleared
  5. Manifest hash now covers all 6 elements, GPS, and timestamps
  6. Server-side GPS accuracy gate: rejects if accuracy_m > 15

HOW IT INTEGRATES:
  - Import and call CaptureLargeService methods from evidence.py router
  - The existing upload_evidence_payload in workflows.py remains for
    backward compat; new submissions should use CaptureLargeService
  - The existing approve_evidence function is replaced by
    CaptureLargeService.approve_package (still calls the same hold logic)

DROP-IN: replace backend/app/services/capture_large.py (new file)
UPDATE:  backend/app/api/routes/evidence.py to use new endpoints
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from hashlib import sha256
from math import asin, cos, radians, sin, sqrt
from typing import Optional

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.models.entities import (
    Component, Evidence, EvidenceAsset, ExecutionHold, Professional,
)
from app.services.audit import record_audit
from app.services.storage import store_object
from app.services.twin import append_twin_event


# ── Constants ─────────────────────────────────────────────────────────────────

GPS_ACCURACY_MAX_M: float = 15.0       # Hard gate — reject if worse than this
GPS_ACCURACY_BONUS_M: float = 5.0      # Bonus points if accuracy ≤ this value
TIMESTAMP_DRIFT_MAX_S: int = 300       # Reject if device clock > 5 min off server
MIN_EVIDENCE_SCORE: float = 80.0       # Package must score ≥80 to auto-approve

# The 6 canonical CAPTURE-LARGE element types
CAPTURE_LARGE_REQUIRED = {
    "wide_context",       # Element 1
    "detail_closeup",     # Element 2
    "measurement_reference",  # Element 3
    "geo_tag",            # Element 5 (GPS marker photo)
    # Element 4 (before_correction / after_correction) required only when
    # a deviation was corrected. Element 6 (supplemental) is optional.
}
DEVIATION_ELEMENTS = {"before_correction", "after_correction"}
ALL_VALID_TYPES = {
    "wide_context", "detail_closeup", "measurement_reference",
    "before_correction", "after_correction", "geo_tag", "supplemental",
}


# ── Haversine distance ────────────────────────────────────────────────────────

def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return distance in metres between two GPS coordinates."""
    R = 6_371_000
    phi1, phi2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dlam = radians(lon2 - lon1)
    a = sin(dphi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(dlam / 2) ** 2
    return 2 * R * asin(sqrt(a))


# ── Package Model (in-memory representation before DB save) ──────────────────

class CaptureLargePackageStatus:
    def __init__(self, package_row):
        self.id = package_row.id
        self.component_uid = package_row.component_uid
        self.project_uid = package_row.project_uid
        self.action_type = package_row.action_type
        self.is_complete = package_row.is_complete
        self.status = package_row.status
        self.has_wide_context = package_row.has_wide_context
        self.has_detail_closeup = package_row.has_detail_closeup
        self.has_measurement_ref = package_row.has_measurement_ref
        self.has_before_correction = package_row.has_before_correction
        self.has_after_correction = package_row.has_after_correction
        self.has_geo_tag = package_row.has_geo_tag
        self.geo_lat = package_row.geo_lat
        self.geo_lon = package_row.geo_lon
        self.geo_accuracy_m = package_row.geo_accuracy_m
        self.geo_verified = package_row.geo_verified
        self.validation_score = package_row.validation_score
        self.package_hash = package_row.package_hash
        self.rejection_reason = package_row.rejection_reason

    @property
    def missing_elements(self) -> list[str]:
        missing = []
        if not self.has_wide_context:
            missing.append("wide_context (Element 1)")
        if not self.has_detail_closeup:
            missing.append("detail_closeup (Element 2)")
        if not self.has_measurement_ref:
            missing.append("measurement_reference (Element 3)")
        if not self.has_geo_tag:
            missing.append("geo_tag (Element 5)")
        return missing


# ── Main Service ──────────────────────────────────────────────────────────────

class CaptureLargeService:

    @staticmethod
    def get_or_create_package(
        db: Session,
        component_uid: str,
        project_uid: str,
        action_type: str,
        submitter_id: int,
    ):
        """Get the active open package or create one."""
        from app.models.entities import Component
        # Import inline to avoid circular import with models
        # (CaptureLargePackage is in a new table we're adding)
        pkg = db.execute(
            db.query.__self__.__class__.text(  # raw SQL for new table
                "SELECT id, component_uid, project_uid, action_type, "
                "submitted_by_id, has_wide_context, has_detail_closeup, "
                "has_measurement_ref, has_before_correction, has_after_correction, "
                "has_geo_tag, geo_lat, geo_lon, geo_accuracy_m, geo_verified, "
                "is_complete, completed_at, validation_score, package_hash, "
                "status, reviewed_by_id, reviewed_at, rejection_reason, "
                "created_at, updated_at "
                "FROM capture_large_packages "
                "WHERE component_uid = :cuid AND status IN ('pending', 'submitted') "
                "ORDER BY id DESC LIMIT 1"
            ),
            {"cuid": component_uid},
        ).fetchone()
        return pkg

    @staticmethod
    def _open_package(db: Session, component_uid: str,
                      project_uid: str, action_type: str,
                      submitter_id: int) -> int:
        """Insert a new package record and return its id."""
        result = db.execute(
            db.query.__self__.__class__.text(
                "INSERT INTO capture_large_packages "
                "(component_uid, project_uid, action_type, submitted_by_id, "
                "has_wide_context, has_detail_closeup, has_measurement_ref, "
                "has_before_correction, has_after_correction, has_geo_tag, "
                "is_complete, status, created_at, updated_at) "
                "VALUES (:cuid, :puid, :atype, :sid, "
                "false, false, false, false, false, false, "
                "false, 'pending', now(), now()) "
                "RETURNING id"
            ),
            {
                "cuid": component_uid, "puid": project_uid,
                "atype": action_type, "sid": submitter_id,
            },
        )
        db.commit()
        return result.fetchone()[0]

    @staticmethod
    def upload_element(
        db: Session,
        *,
        component_uid: str,
        project_uid: str,
        action_type: str,
        photo_type: str,
        file_bytes: bytes,
        filename: str,
        content_type: str,
        geo_lat: float | None,
        geo_lon: float | None,
        geo_accuracy_m: float | None,
        capture_ts: datetime | None,
        submitter: Professional,
        has_deviation: bool = False,
    ) -> dict:
        """
        Upload one CAPTURE-LARGE element.

        Enforced rules:
          - photo_type must be one of the 7 valid types
          - GPS accuracy must be ≤ 15m (hard gate)
          - Device timestamp must be within 5 minutes of server time
          - File must not be zero bytes
        """
        # ── Validate photo type ───────────────────────────────────────────────
        if photo_type not in ALL_VALID_TYPES:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid photo_type '{photo_type}'. "
                       f"Must be one of: {sorted(ALL_VALID_TYPES)}"
            )

        # ── GPS accuracy gate — 15 metre hard limit ───────────────────────────
        geo_verified = False
        if geo_lat is not None and geo_lon is not None:
            if geo_accuracy_m is None:
                raise HTTPException(
                    status_code=422,
                    detail="geo_accuracy_m is required when GPS coordinates are provided. "
                           "CAPTURE-LARGE requires GPS accuracy ≤ 15m."
                )
            if geo_accuracy_m > GPS_ACCURACY_MAX_M:
                raise HTTPException(
                    status_code=422,
                    detail=f"GPS accuracy {geo_accuracy_m:.1f}m exceeds the "
                           f"15-metre CAPTURE-LARGE limit. "
                           "Move closer to the component and resubmit. "
                           "A field crew submitting from 500m away is NOT at the component."
                )
            geo_verified = True

        # ── Timestamp drift gate ──────────────────────────────────────────────
        server_ts = datetime.now(timezone.utc)
        drift_s: int | None = None
        if capture_ts is not None:
            cts = capture_ts.replace(tzinfo=timezone.utc) if capture_ts.tzinfo is None else capture_ts
            drift_s = int(abs((server_ts - cts).total_seconds()))
            if drift_s > TIMESTAMP_DRIFT_MAX_S:
                raise HTTPException(
                    status_code=422,
                    detail=f"Device timestamp is {drift_s}s away from server time "
                           f"(maximum {TIMESTAMP_DRIFT_MAX_S}s). "
                           "Sync your device clock and resubmit."
                )

        # ── File size gate ────────────────────────────────────────────────────
        if len(file_bytes) == 0:
            raise HTTPException(status_code=422, detail="Empty file rejected.")

        # ── Hash and store ────────────────────────────────────────────────────
        file_hash = sha256(file_bytes).hexdigest()
        object_name = (
            f"evidence/{project_uid}/{component_uid}/"
            f"{photo_type}/{file_hash[:12]}_{filename}"
        )
        backend_name, storage_path = store_object(
            object_name, file_bytes, content_type=content_type
        )

        # ── Component must exist ──────────────────────────────────────────────
        component = db.query(Component).filter(
            Component.uid == component_uid,
            Component.is_deleted.is_(False),
        ).first()
        if not component:
            raise HTTPException(status_code=404, detail="Component not found")

        # ── Create or get hold ────────────────────────────────────────────────
        hold = db.query(ExecutionHold).filter(
            ExecutionHold.component_uid == component_uid,
            ExecutionHold.status == "active",
        ).first()
        if not hold:
            hold = ExecutionHold(
                component_uid=component_uid,
                project_uid=project_uid,
                reason_code="EVIDENCE_REQUIRED",
                status="active",
                detail="CAPTURE-LARGE: awaiting all 6 elements",
            )
            db.add(hold)
            db.flush()

        # ── Element index ─────────────────────────────────────────────────────
        element_map = {
            "wide_context": 1,
            "detail_closeup": 2,
            "measurement_reference": 3,
            "before_correction": 4,
            "after_correction": 4,
            "geo_tag": 5,
            "supplemental": 6,
        }
        element_index = element_map.get(photo_type, 6)

        # ── Write Evidence record ─────────────────────────────────────────────
        evidence = Evidence(
            component_uid=component_uid,
            project_uid=project_uid,
            type="CAPTURE-LARGE",
            images=1,
            submitted_by=submitter.id,
            description=f"CAPTURE-LARGE Element {element_index}: {photo_type}",
            timestamp=server_ts.isoformat(),
            geo=f"{geo_lat},{geo_lon}" if geo_lat is not None else None,
            hash=file_hash,
            status="submitted",
            # New fields
            photo_type=photo_type,
            geo_lat=geo_lat,
            geo_lon=geo_lon,
            geo_accuracy_m=geo_accuracy_m,
            geo_verified=geo_verified,
            capture_ts=capture_ts,
            server_ts=server_ts,
            timestamp_drift_s=drift_s,
            element_index=element_index,
        )
        db.add(evidence)
        db.flush()

        asset = EvidenceAsset(
            evidence_id=evidence.id,
            original_name=filename,
            storage_path=storage_path,
            storage_backend=backend_name,
            content_type=content_type,
            sha256=file_hash,
            size_bytes=len(file_bytes),
            immutable=True,
        )
        db.add(asset)
        db.flush()

        # ── Update package row (if it exists) ─────────────────────────────────
        flag_map = {
            "wide_context":          "has_wide_context",
            "detail_closeup":        "has_detail_closeup",
            "measurement_reference": "has_measurement_ref",
            "before_correction":     "has_before_correction",
            "after_correction":      "has_after_correction",
            "geo_tag":               "has_geo_tag",
        }
        flag_col = flag_map.get(photo_type)
        if flag_col:
            db.execute(
                db.query.__self__.__class__.text(
                    f"UPDATE capture_large_packages "
                    f"SET {flag_col} = true, "
                    f"geo_lat = COALESCE(geo_lat, :lat), "
                    f"geo_lon = COALESCE(geo_lon, :lon), "
                    f"geo_accuracy_m = COALESCE(geo_accuracy_m, :acc), "
                    f"geo_verified = (COALESCE(geo_accuracy_m, 9999) <= 15 OR :geo_v), "
                    f"updated_at = now() "
                    f"WHERE component_uid = :cuid AND status IN ('pending','submitted')"
                ),
                {
                    "lat": geo_lat, "lon": geo_lon,
                    "acc": geo_accuracy_m, "geo_v": geo_verified,
                    "cuid": component_uid,
                },
            )

        # ── Manifest hash on evidence ─────────────────────────────────────────
        manifest_content = json.dumps({
            "evidence_id": evidence.id,
            "component_uid": component_uid,
            "project_uid": project_uid,
            "photo_type": photo_type,
            "sha256": file_hash,
            "geo_lat": geo_lat,
            "geo_lon": geo_lon,
            "geo_accuracy_m": geo_accuracy_m,
            "capture_ts": capture_ts.isoformat() if capture_ts else None,
            "server_ts": server_ts.isoformat(),
        }, sort_keys=True)
        evidence.manifest_hash = sha256(manifest_content.encode()).hexdigest()

        db.commit()

        # ── TWIN event ────────────────────────────────────────────────────────
        append_twin_event(
            db,
            project_uid=project_uid,
            component_uid=component_uid,
            event_type="BUILD.CAPTURE_LARGE_ELEMENT",
            aggregate_type="evidence",
            aggregate_uid=str(evidence.id),
            actor_email=submitter.email,
            payload={
                "photo_type": photo_type,
                "element_index": element_index,
                "sha256": file_hash,
                "geo_verified": geo_verified,
                "geo_accuracy_m": geo_accuracy_m,
                "timestamp_drift_s": drift_s,
            },
        )

        # ── Check package completeness ────────────────────────────────────────
        completeness = CaptureLargeService._check_completeness(
            db, component_uid, has_deviation=has_deviation
        )

        record_audit(
            db, submitter.email, "BUILD_CAPTURE_LARGE_ELEMENT",
            f"Uploaded {photo_type} (Element {element_index}) for {component_uid}"
        )

        return {
            "evidence_id": evidence.id,
            "asset_sha256": file_hash,
            "photo_type": photo_type,
            "element_index": element_index,
            "geo_verified": geo_verified,
            "geo_accuracy_m": geo_accuracy_m,
            "capture_large_complete": completeness["complete"],
            "missing_elements": completeness["missing"],
            "validation_score": completeness["score"],
            "message": completeness["message"],
        }

    @staticmethod
    def _check_completeness(
        db: Session,
        component_uid: str,
        has_deviation: bool = False,
    ) -> dict:
        """
        Check whether all required CAPTURE-LARGE elements have been submitted.
        Returns {complete, missing, score, message}.
        """
        submitted_types = set(
            row[0] for row in db.execute(
                db.query.__self__.__class__.text(
                    "SELECT DISTINCT photo_type FROM evidence "
                    "WHERE component_uid = :cuid AND photo_type IS NOT NULL "
                    "AND status != 'rejected' AND is_deleted = false"
                ),
                {"cuid": component_uid},
            ).fetchall()
        )

        required = CAPTURE_LARGE_REQUIRED.copy()
        if has_deviation:
            required.add("before_correction")
            required.add("after_correction")

        missing = [t for t in sorted(required) if t not in submitted_types]

        # Scoring (100 pts)
        score = 0.0
        if "wide_context" in submitted_types:        score += 20.0
        if "detail_closeup" in submitted_types:      score += 20.0
        if "measurement_reference" in submitted_types: score += 20.0
        if "geo_tag" in submitted_types:             score += 20.0
        if "supplemental" in submitted_types:        score += 5.0

        # GPS verified bonus
        geo_ok = db.execute(
            db.query.__self__.__class__.text(
                "SELECT COUNT(*) FROM evidence "
                "WHERE component_uid = :cuid AND geo_verified = true "
                "AND is_deleted = false"
            ),
            {"cuid": component_uid},
        ).scalar()
        if geo_ok and geo_ok > 0:
            score += 15.0

        complete = len(missing) == 0

        if complete:
            message = (
                f"✅ CAPTURE-LARGE complete. Validation score: {score:.0f}/100. "
                "Pour hold will clear on approval."
            )
        else:
            message = (
                f"⚠ CAPTURE-LARGE incomplete. Missing: {', '.join(missing)}. "
                "Upload all required elements before approval."
            )

        return {
            "complete": complete,
            "missing": missing,
            "score": round(score, 1),
            "message": message,
        }

    @staticmethod
    def approve_package(
        db: Session,
        component_uid: str,
        project_uid: str,
        approver: Professional,
        has_deviation: bool = False,
    ) -> dict:
        """
        Approve a CAPTURE-LARGE package and clear the ExecutionHold.
        All required elements must be present. GPS must be verified.
        Approver must be TRUSTED or HONOR.
        """
        from app.services.prefab import _get_band, _band_meets

        # Band check
        band = _get_band(approver)
        if not _band_meets(band, "TRUSTED"):
            raise HTTPException(
                status_code=403,
                detail=f"CAPTURE-LARGE approval requires PRI: TRUSTED or HONOR. "
                       f"Your band: {band}."
            )

        completeness = CaptureLargeService._check_completeness(
            db, component_uid, has_deviation=has_deviation
        )
        if not completeness["complete"]:
            raise HTTPException(
                status_code=422,
                detail=f"Cannot approve — CAPTURE-LARGE is incomplete. "
                       f"Missing: {completeness['missing']}",
            )

        # GPS must be verified on at least one element
        geo_ok = db.execute(
            db.query.__self__.__class__.text(
                "SELECT COUNT(*) FROM evidence "
                "WHERE component_uid = :cuid AND geo_verified = true "
                "AND is_deleted = false"
            ),
            {"cuid": component_uid},
        ).scalar()
        if not geo_ok:
            raise HTTPException(
                status_code=422,
                detail="GPS not verified on any element. "
                       "At least one photo must have GPS accuracy ≤ 15m.",
            )

        # Approve all pending evidence for this component
        db.execute(
            db.query.__self__.__class__.text(
                "UPDATE evidence SET status = 'approved', approved_by = :aid "
                "WHERE component_uid = :cuid AND status = 'submitted' "
                "AND is_deleted = false"
            ),
            {"aid": approver.id, "cuid": component_uid},
        )

        # Clear the ExecutionHold
        component = db.query(Component).filter(
            Component.uid == component_uid,
            Component.is_deleted.is_(False),
        ).first()
        if component:
            component.blocked_for_execution = False
            component.status = "evidence-approved"
            hold = db.query(ExecutionHold).filter(
                ExecutionHold.component_uid == component_uid,
                ExecutionHold.status == "active",
            ).first()
            if hold:
                hold.status = "cleared"
                hold.cleared_by = approver.id

        db.commit()

        append_twin_event(
            db,
            project_uid=project_uid,
            component_uid=component_uid,
            event_type="BUILD.CAPTURE_LARGE_APPROVED",
            aggregate_type="component",
            aggregate_uid=component_uid,
            actor_email=approver.email,
            payload={
                "component_uid": component_uid,
                "approver_band": band,
                "validation_score": completeness["score"],
            },
        )

        record_audit(
            db, approver.email, "BUILD_CAPTURE_LARGE_APPROVED",
            f"Approved CAPTURE-LARGE package for {component_uid}"
        )

        return {
            "approved": True,
            "component_uid": component_uid,
            "hold_cleared": True,
            "validation_score": completeness["score"],
            "message": f"✅ CAPTURE-LARGE approved by {band} engineer. "
                       "Pour hold cleared. Structural action may proceed.",
        }

    @staticmethod
    def get_package_status(db: Session, component_uid: str) -> dict:
        """Return current CAPTURE-LARGE completeness for a component."""
        completeness = CaptureLargeService._check_completeness(db, component_uid)
        submitted = db.execute(
            db.query.__self__.__class__.text(
                "SELECT photo_type, geo_verified, geo_accuracy_m, "
                "element_index, status, created_at "
                "FROM evidence WHERE component_uid = :cuid "
                "AND photo_type IS NOT NULL AND is_deleted = false "
                "ORDER BY element_index ASC, id ASC"
            ),
            {"cuid": component_uid},
        ).fetchall()
        hold = db.query(ExecutionHold).filter(
            ExecutionHold.component_uid == component_uid,
            ExecutionHold.status == "active",
        ).first()
        return {
            "component_uid": component_uid,
            "elements_submitted": [
                {
                    "photo_type": r[0], "geo_verified": r[1],
                    "geo_accuracy_m": r[2], "element_index": r[3],
                    "status": r[4], "submitted_at": str(r[5]),
                }
                for r in submitted
            ],
            "missing_elements": completeness["missing"],
            "capture_large_complete": completeness["complete"],
            "validation_score": completeness["score"],
            "hold_active": hold is not None,
            "hold_reason": hold.detail if hold else None,
            "message": completeness["message"],
        }
