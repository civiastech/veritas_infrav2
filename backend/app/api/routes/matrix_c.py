"""
VERITAS INFRA™ — MATRIX-C™ API Router
Multi-factor bid evaluation with anti-corruption scoring.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional

from app.api.deps import require_action
from app.db.session import get_db
from app.models.entities import Professional
from app.services.matrix_c import evaluate_bid_matrix_c, rank_all_bids

router = APIRouter(prefix="/matrix-c", tags=["MATRIX-C™ — Bid Evaluation"])


class CapacityData(BaseModel):
    years_experience: int = Field(ge=0, default=0)
    similar_projects_count: int = Field(ge=0, default=0)
    team_size: int = Field(ge=0, default=0)
    equipment_score: float = Field(ge=0.0, le=100.0, default=0.0)


class IntegrityData(BaseModel):
    certified_compliance_system: bool = False
    anti_bribery_policy: bool = False
    past_violations: int = Field(ge=0, default=0)
    platform_months: int = Field(ge=0, default=0)


class EvaluateBidPayload(BaseModel):
    lead_professional_id: Optional[int] = None
    capacity: CapacityData = Field(default_factory=CapacityData)
    integrity: IntegrityData = Field(default_factory=IntegrityData)


@router.post("/bids/{bid_id}/evaluate",
             summary="Run MATRIX-C evaluation on a bid")
def evaluate_bid(
    bid_id: int,
    payload: EvaluateBidPayload,
    db: Session = Depends(get_db),
    current_user: Professional = Depends(require_action("tenders:write")),
):
    try:
        result = evaluate_bid_matrix_c(
            db=db,
            bid_id=bid_id,
            lead_professional_id=payload.lead_professional_id,
            capacity_data=payload.capacity.model_dump(),
            integrity_data=payload.integrity.model_dump(),
            evaluator=current_user,
        )
        return result
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.get("/tenders/{tender_uid}/ranking",
            summary="Get MATRIX-C ranked bid list for a tender")
def bid_ranking(
    tender_uid: str,
    db: Session = Depends(get_db),
    current_user: Professional = Depends(require_action("tenders:read")),
):
    ranked = rank_all_bids(db, tender_uid, current_user)
    return {"tender_uid": tender_uid, "count": len(ranked), "ranked_bids": ranked}
