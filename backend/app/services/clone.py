from collections import defaultdict
from sqlalchemy.orm import Session
from app.models.entities import Country, CountryTenant, LaunchProgram

def build_rollout_summary(db: Session) -> dict:
    countries = db.query(Country).filter(Country.is_deleted.is_(False)).all()
    tenants = db.query(CountryTenant).filter(CountryTenant.is_deleted.is_(False), CountryTenant.launch_status.in_(["active","launched","pilot"])).all()
    programs = db.query(LaunchProgram).filter(LaunchProgram.is_deleted.is_(False), LaunchProgram.status == 'active').all()
    rows = []
    by_code = defaultdict(dict)
    for c in countries:
        by_code[c.code] = {
            'country_code': c.code,
            'country_name': c.name,
            'launch_stage': c.launch_stage,
            'readiness_score': c.readiness_score,
            'tenant_count': 0,
            'active_programs': 0,
        }
    for t in tenants:
        if t.country_code in by_code:
            by_code[t.country_code]['tenant_count'] += 1
    for p in programs:
        if p.country_code in by_code:
            by_code[p.country_code]['active_programs'] += 1
    rows = sorted(by_code.values(), key=lambda x: x['readiness_score'], reverse=True)
    return {
        'total_countries': len(countries),
        'active_tenants': len(tenants),
        'avg_readiness': round(sum((c.readiness_score or 0) for c in countries) / len(countries), 2) if countries else 0,
        'launches_in_progress': len([p for p in programs if p.progress < 100]),
        'countries': rows,
    }
