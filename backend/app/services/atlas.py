
from collections import defaultdict
from sqlalchemy.orm import Session
from app.models.entities import Project, MonitorAlert, Certification, Payment, Professional


def build_portfolio_summary(db: Session, country: str | None = None) -> dict:
    q = db.query(Project).filter(Project.is_deleted.is_(False))
    if country:
        q = q.filter(Project.country == country)
    projects = q.all()
    active_projects = [p for p in projects if p.status == 'active']
    avg_shi = round(sum((p.shi or 0) for p in projects) / len(projects), 2) if projects else 0
    countries = defaultdict(lambda: {'country': '', 'projects': 0, 'avg_shi': 0.0, 'project_value': 0.0})
    for p in projects:
        key = p.country or 'Unknown'
        countries[key]['country'] = key
        countries[key]['projects'] += 1
        countries[key]['avg_shi'] += p.shi or 0
        countries[key]['project_value'] += p.value or 0
    rows = []
    for v in countries.values():
        v['avg_shi'] = round(v['avg_shi'] / v['projects'], 2) if v['projects'] else 0
        rows.append(v)
    project_uids = [p.uid for p in projects] or ['']
    alerts_q = db.query(MonitorAlert).filter(MonitorAlert.status == 'open', MonitorAlert.project_uid.in_(project_uids))
    cert_q = db.query(Certification).filter(Certification.is_deleted.is_(False), Certification.project_uid.in_(project_uids), Certification.status.in_(['issued','pending_ceremony']))
    payments_q = db.query(Payment).filter(Payment.is_deleted.is_(False), Payment.project_uid.in_(project_uids), Payment.status == 'completed')
    pros_q = db.query(Professional).filter(Professional.is_deleted.is_(False), Professional.active.is_(True))
    if country:
        pros_q = pros_q.filter(Professional.country == country)
    pros = pros_q.all()
    return {
        'total_projects': len(projects),
        'active_projects': len(active_projects),
        'avg_shi': avg_shi,
        'total_project_value': round(sum(p.value or 0 for p in projects), 2),
        'countries': sorted(rows, key=lambda x: x['projects'], reverse=True),
        'open_alerts': alerts_q.count(),
        'certified_projects': cert_q.count(),
        'payment_released_total': round(sum(p.amount or 0 for p in payments_q.all()), 2),
        'professionalism_index_avg': round(sum((p.pri_score or 0) for p in pros) / len(pros), 2) if pros else 0,
    }
