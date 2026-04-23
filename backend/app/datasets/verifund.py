from sqlalchemy.orm import Session
from app.models.entities import FinancialProduct, UnderwritingApplication
from app.seed.utils import get_professional_id_by_email

REQUIRES = ["financial_products", "underwriting_applications", "projects", "professionals"]

PRODUCTS = [
    {
        "code": "VF-GUARANTEE-STD",
        "name": "Structural Integrity Guarantee",
        "category": "guarantee",
        "description": "Guarantee instrument priced from TWIN/SHI indicators.",
        "base_rate_bps": 125,
        "min_shi": 82,
        "active": True,
    },
    {
        "code": "VF-INSURE-PREM",
        "name": "Certified Asset Premium Cover",
        "category": "insurance",
        "description": "Enhanced insurance cover for SEAL-ready projects.",
        "base_rate_bps": 95,
        "min_shi": 85,
        "active": True,
    },
]

APPLICATIONS = [
    {
        "application_uid": "UW-2026-001",
        "project_uid": "BLD-GHA-001-2026",
        "product_code": "VF-INSURE-PREM",
        "applicant_name": "Goldcoast Properties Ltd",
        "requested_amount": 12000000,
        "currency": "USD",
        "status": "submitted",
        "submitted_by_email": "admin@visc.org",
    }
]

def seed(db: Session) -> None:
    for row in PRODUCTS:
        existing = db.query(FinancialProduct).filter(FinancialProduct.code == row["code"]).first()
        if existing:
            for k, v in row.items():
                setattr(existing, k, v)
        else:
            db.add(FinancialProduct(**row))

    db.flush()

    for row in APPLICATIONS:
        payload = dict(row)
        payload["submitted_by"] = get_professional_id_by_email(db, payload.pop("submitted_by_email"))

        existing = (
            db.query(UnderwritingApplication)
            .filter(UnderwritingApplication.application_uid == payload["application_uid"])
            .first()
        )
        if existing:
            for k, v in payload.items():
                setattr(existing, k, v)
        else:
            db.add(UnderwritingApplication(**payload))