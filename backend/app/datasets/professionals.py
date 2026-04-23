from sqlalchemy.orm import Session
from app.models.entities import Professional
from app.core.security import get_password_hash

REQUIRES = ["professionals"]

DATA = [
    {
        "name": "Admin User",
        "email": "admin@visc.org",
        "role": "admin",
        "band": "ADMIN",
        "discipline": "Platform Administration",
        "country": "Nigeria",
        "projects": 0,
        "shi_avg": 0.0,
        "pri_score": 100.0,
        "hashed_password": "AdminPass123!",
    },
    {
        "name": "Engr. Adaora Okonkwo",
        "email": "a.okonkwo@visc.org",
        "role": "engineer",
        "band": "HONOR",
        "discipline": "Structural Engineering",
        "country": "Nigeria",
        "projects": 47,
        "shi_avg": 94.2,
        "pri_score": 96.0,
    },
]

def seed(db: Session) -> None:
    for row in DATA:
        existing = db.query(Professional).filter(Professional.email == row["email"]).first()

        payload = dict(row)
        if "hashed_password" in payload:
            payload["hashed_password"] = get_password_hash(payload["hashed_password"])

        if existing:
            for key, value in payload.items():
                setattr(existing, key, value)
        else:
            db.add(Professional(**payload))