"""
VERITAS INFRA™ — MATRIX-C™ Bid Evaluation Engine
Priority 8: Full multi-factor bid evaluation with anti-corruption scoring.

MATRIX-C evaluates contractor bids across 5 weighted dimensions:
  PRI Score (30%) — Professional Responsibility Index of lead team
  Price Rationality Index (25%) — How reasonable the price is vs market
  SHI History (25%) — Past structural performance on completed projects
  Technical Capacity (15%) — Equipment, team size, similar project history
  Integrity Commitment (5%) — Evidence of compliance culture

Price Rationality Index (PRI-bid):
  = bid_price / median_of_all_bids
  < 0.70 → automatic flag (abnormally low — potential dumping fraud)
  > 1.35 → automatic flag (abnormally high)
  0.70–1.35 → within acceptable range
"""
from __future__ import annotations

import statistics
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.entities import Bid, Inspection, Professional, Tender
from app.services.audit import record_audit
from app.services.twin import append_twin_event


# ── Weights ───────────────────────────────────────────────────────────────────

WEIGHT_PRI         = 0.30
WEIGHT_PRICE       = 0.25
WEIGHT_SHI_HISTORY = 0.25
WEIGHT_CAPACITY    = 0.15
WEIGHT_INTEGRITY   = 0.05

# Price Rationality thresholds
PRI_BID_LOW_FLAG   = 0.70
PRI_BID_HIGH_FLAG  = 1.35
PRI_BID_OPTIMAL_L  = 0.85
PRI_BID_OPTIMAL_H  = 1.15


def _get_band(score: float) -> str:
    if score >= 85:
        return "HONOR"
    elif score >= 70:
        return "TRUSTED"
    elif score >= 50:
        return "STABLE"
    return "PROVISIONAL"


# ── Sub-Score Computations ────────────────────────────────────────────────────

def _score_pri(lead_professional_pri: float) -> float:
    if lead_professional_pri >= 85:
        return 100.0
    elif lead_professional_pri >= 70:
        return 80.0 + (lead_professional_pri - 70) * 1.33
    elif lead_professional_pri >= 50:
        return 60.0 + (lead_professional_pri - 50) * 1.0
    elif lead_professional_pri > 0:
        return 20.0 + lead_professional_pri * 0.8
    return 0.0


def _score_price_rationality(
    bid_price: float,
    all_bid_prices: list[float],
) -> tuple[float, float, bool, str]:
    if not all_bid_prices or len(all_bid_prices) < 2:
        return 70.0, 1.0, False, "Insufficient bids for PRI computation"

    median_price = statistics.median(all_bid_prices)
    if median_price == 0:
        return 0.0, 0.0, True, "Zero median bid price — data error"

    ratio = bid_price / median_price
    flagged = False
    flag_reason = ""

    if ratio < PRI_BID_LOW_FLAG:
        flagged = True
        flag_reason = (
            f"Price Rationality Index {ratio:.3f} is below {PRI_BID_LOW_FLAG} "
            "(abnormally low — possible dumping, fraud, or unqualified estimate). "
            "This bid requires manual review before award."
        )
        normalized = 20.0
    elif ratio > PRI_BID_HIGH_FLAG:
        flagged = True
        flag_reason = (
            f"Price Rationality Index {ratio:.3f} exceeds {PRI_BID_HIGH_FLAG} "
            "(abnormally high). Review for market manipulation."
        )
        normalized = 40.0
    elif PRI_BID_OPTIMAL_L <= ratio <= PRI_BID_OPTIMAL_H:
        normalized = 100.0
    elif ratio < PRI_BID_OPTIMAL_L:
        normalized = 60.0 + ((ratio - PRI_BID_LOW_FLAG) /
                             (PRI_BID_OPTIMAL_L - PRI_BID_LOW_FLAG)) * 40.0
    else:
        normalized = 60.0 + ((PRI_BID_HIGH_FLAG - ratio) /
                             (PRI_BID_HIGH_FLAG - PRI_BID_OPTIMAL_H)) * 40.0

    return round(max(0.0, min(100.0, normalized)), 2), round(ratio, 4), flagged, flag_reason


def _score_shi_history(avg_shi: float) -> float:
    if avg_shi >= 90:
        return 100.0
    elif avg_shi >= 80:
        return 80.0 + (avg_shi - 80) * 2.0
    elif avg_shi >= 75:
        return 60.0 + (avg_shi - 75) * 4.0
    elif avg_shi >= 70:
        return 40.0 + (avg_shi - 70) * 4.0
    elif avg_shi > 0:
        return avg_shi * 40.0 / 70.0
    return 0.0


def _score_capacity(
    years_experience: int,
    similar_projects_count: int,
    team_size: int,
    equipment_score: float,
) -> float:
    exp_score = min(100.0, years_experience * 5.0)
    proj_score = min(100.0, similar_projects_count * 10.0)
    team_score = min(100.0, team_size * 2.0)
    equip_score = max(0.0, min(100.0, equipment_score))

    return round(
        0.30 * exp_score + 0.30 * proj_score +
        0.20 * team_score + 0.20 * equip_score,
        2
    )


def _score_integrity_commitment(
    certified_compliance_system: bool,
    anti_bribery_policy: bool,
    past_violations: int,
    platform_months: int,
) -> float:
    score = 50.0
    if certified_compliance_system:
        score += 20.0
    if anti_bribery_policy:
        score += 15.0
    if past_violations == 0:
        score += 15.0
    else:
        score -= past_violations * 10.0
    score += min(15.0, platform_months * 0.5)
    return round(max(0.0, min(100.0, score)), 2)


# ── Full MATRIX-C Evaluation ──────────────────────────────────────────────────

def evaluate_bid_matrix_c(
    db: Session,
    bid_id: int,
    lead_professional_id: int | None,
    capacity_data: dict,
    integrity_data: dict,
    evaluator: Professional,
) -> dict:
    bid = db.query(Bid).filter(Bid.id == bid_id).first()
    if not bid:
        raise ValueError(f"Bid {bid_id} not found")

    tender = db.query(Tender).filter(
        Tender.uid == bid.tender_uid,
        Tender.is_deleted.is_(False),
    ).first()
    if not tender:
        raise ValueError(f"Tender {bid.tender_uid} not found")

    all_bids = db.query(Bid).filter(
        Bid.tender_uid == bid.tender_uid,
        Bid.status != "withdrawn",
        Bid.is_deleted.is_(False),
    ).all()
    all_prices = [b.price for b in all_bids if b.price > 0]

    # 1. PRI sub-score
    lead_pri = 0.0
    lead_band = "PROVISIONAL"
    if lead_professional_id:
        lead_prof = db.query(Professional).filter(
            Professional.id == lead_professional_id
        ).first()
        if lead_prof:
            lead_pri = lead_prof.pri_score or 0.0
            lead_band = _get_band(lead_pri)
    pri_subscore = _score_pri(lead_pri)

    # 2. Price Rationality
    price_subscore, pri_bid_ratio, price_flagged, price_flag_reason = (
        _score_price_rationality(bid.price, all_prices)
    )

    # 3. SHI History
    shi_subscore = _score_shi_history(bid.shi_history or 0.0)

    # 4. Technical Capacity
    capacity_subscore = _score_capacity(
        years_experience=capacity_data.get("years_experience", 0),
        similar_projects_count=capacity_data.get("similar_projects_count", 0),
        team_size=capacity_data.get("team_size", 0),
        equipment_score=capacity_data.get("equipment_score", 0),
    )

    # 5. Integrity Commitment
    integrity_subscore = _score_integrity_commitment(
        certified_compliance_system=integrity_data.get(
            "certified_compliance_system", False
        ),
        anti_bribery_policy=integrity_data.get("anti_bribery_policy", False),
        past_violations=integrity_data.get("past_violations", 0),
        platform_months=integrity_data.get("platform_months", 0),
    )

    # MATRIX-C composite
    matrix_score = round(
        WEIGHT_PRI         * pri_subscore
        + WEIGHT_PRICE     * price_subscore
        + WEIGHT_SHI_HISTORY * shi_subscore
        + WEIGHT_CAPACITY  * capacity_subscore
        + WEIGHT_INTEGRITY * integrity_subscore,
        2
    )

    recommendation = _generate_recommendation(
        matrix_score, price_flagged, lead_band
    )

    bid.matrix_score = matrix_score
    bid.integrity_score = integrity_subscore
    bid.capacity_score = capacity_subscore
    db.commit()

    result = {
        "bid_id": bid_id,
        "tender_uid": bid.tender_uid,
        "firm": bid.firm,
        "bid_price": bid.price,
        "bid_price_currency": tender.currency,
        "matrix_score": matrix_score,
        "recommendation": recommendation,
        "price_rationality_index": pri_bid_ratio,
        "price_flagged": price_flagged,
        "price_flag_reason": price_flag_reason,
        "sub_scores": {
            "pri_score": {
                "raw_pri": lead_pri,
                "band": lead_band,
                "normalized_0_100": pri_subscore,
                "weight": "30%",
                "weighted_contribution": round(WEIGHT_PRI * pri_subscore, 2),
            },
            "price_rationality": {
                "bid_price": bid.price,
                "median_bid": statistics.median(all_prices) if all_prices else 0,
                "pri_bid_ratio": pri_bid_ratio,
                "normalized_0_100": price_subscore,
                "weight": "25%",
                "flagged": price_flagged,
                "weighted_contribution": round(WEIGHT_PRICE * price_subscore, 2),
            },
            "shi_history": {
                "avg_shi": bid.shi_history or 0.0,
                "normalized_0_100": shi_subscore,
                "weight": "25%",
                "weighted_contribution": round(WEIGHT_SHI_HISTORY * shi_subscore, 2),
            },
            "technical_capacity": {
                "normalized_0_100": capacity_subscore,
                "weight": "15%",
                "weighted_contribution": round(WEIGHT_CAPACITY * capacity_subscore, 2),
                "detail": capacity_data,
            },
            "integrity_commitment": {
                "normalized_0_100": integrity_subscore,
                "weight": "5%",
                "weighted_contribution": round(WEIGHT_INTEGRITY * integrity_subscore, 2),
                "detail": integrity_data,
            },
        },
        "evaluated_by": evaluator.email,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }

    record_audit(
        db, evaluator.email, "MATRIX_C_EVALUATION",
        f"MATRIX-C evaluated bid {bid_id} — score {matrix_score:.1f}"
    )
    return result


def rank_all_bids(
    db: Session,
    tender_uid: str,
    evaluator: Professional,
) -> list[dict]:
    bids = db.query(Bid).filter(
        Bid.tender_uid == tender_uid,
        Bid.status != "withdrawn",
        Bid.is_deleted.is_(False),
    ).order_by(Bid.matrix_score.desc()).all()

    all_prices = [b.price for b in bids if b.price > 0]
    median_price = statistics.median(all_prices) if all_prices else 0

    ranked = []
    for rank, bid in enumerate(bids, start=1):
        ratio = bid.price / median_price if median_price else 0
        flagged = ratio < PRI_BID_LOW_FLAG or ratio > PRI_BID_HIGH_FLAG
        ranked.append({
            "rank": rank,
            "bid_id": bid.id,
            "firm": bid.firm,
            "price": bid.price,
            "price_rationality_index": round(ratio, 3),
            "price_flagged": flagged,
            "matrix_score": bid.matrix_score or 0,
            "integrity_score": bid.integrity_score or 0,
            "capacity_score": bid.capacity_score or 0,
            "shi_history": bid.shi_history or 0,
            "status": bid.status,
        })

    record_audit(
        db, evaluator.email, "MATRIX_C_RANKING",
        f"MATRIX-C ranking produced for tender {tender_uid} — {len(ranked)} bids"
    )
    return ranked


def _generate_recommendation(
    matrix_score: float,
    price_flagged: bool,
    lead_band: str,
) -> str:
    if price_flagged:
        return "MANUAL REVIEW REQUIRED — Price flag. Do not award without independent verification."
    elif matrix_score >= 80 and lead_band in ("TRUSTED", "HONOR"):
        return "RECOMMENDED — Strong MATRIX-C score with qualified lead professional."
    elif matrix_score >= 70:
        return "ACCEPTABLE — Meets minimum threshold. Standard due diligence applies."
    elif matrix_score >= 60:
        return "CONDITIONAL — Below optimal. Require additional references before award."
    else:
        return "NOT RECOMMENDED — MATRIX-C score below acceptable threshold."
