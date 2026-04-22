from collections import defaultdict
from sqlalchemy.orm import Session
from app.models.entities import Country, Consultation, ComplianceMapping, Regulation

def build_regulatory_readiness(db: Session) -> dict:
    countries = db.query(Country).filter(Country.is_deleted.is_(False)).all()
    consultations = db.query(Consultation).filter(Consultation.is_deleted.is_(False), Consultation.status == 'open').all()
    mappings = db.query(ComplianceMapping).filter(ComplianceMapping.is_deleted.is_(False)).all()
    drafts = db.query(Regulation).filter(Regulation.is_deleted.is_(False), Regulation.status == 'draft').all()
    rows = defaultdict(lambda: {'country_code': '', 'open_consultations': 0, 'mapped_requirements': 0, 'draft_regulations': 0})
    for c in countries:
        rows[c.code]['country_code'] = c.code
    for c in consultations:
        rows[c.country_code]['country_code'] = c.country_code
        rows[c.country_code]['open_consultations'] += 1
    for m in mappings:
        rows[m.country_code]['country_code'] = m.country_code
        rows[m.country_code]['mapped_requirements'] += 1
    for d in drafts:
        rows[d.country_code]['country_code'] = d.country_code
        rows[d.country_code]['draft_regulations'] += 1
    return {
        'tracked_countries': len(countries),
        'open_consultations': len(consultations),
        'mapped_requirements': len(mappings),
        'draft_regulations': len(drafts),
        'countries': sorted(rows.values(), key=lambda x: x['country_code']),
    }
