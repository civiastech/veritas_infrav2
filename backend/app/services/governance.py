from sqlalchemy.orm import Session
from app.models.entities import CSTMember, GovernanceCommittee, GovernanceResolution, AuthorityDelegation

def build_governance_dashboard(db: Session) -> dict:
    active_members = db.query(CSTMember).filter(CSTMember.is_deleted.is_(False), CSTMember.status == 'active').count()
    active_committees = db.query(GovernanceCommittee).filter(GovernanceCommittee.is_deleted.is_(False), GovernanceCommittee.status == 'active').count()
    open_resolutions = db.query(GovernanceResolution).filter(GovernanceResolution.is_deleted.is_(False), GovernanceResolution.status.in_(['draft','review','open'])).count()
    passed_resolutions = db.query(GovernanceResolution).filter(GovernanceResolution.is_deleted.is_(False), GovernanceResolution.status.in_(['passed','issued','effective'])).count()
    delegated_authorities = db.query(AuthorityDelegation).filter(AuthorityDelegation.is_deleted.is_(False), AuthorityDelegation.status == 'active').count()
    return {
        'active_members': active_members,
        'active_committees': active_committees,
        'open_resolutions': open_resolutions,
        'passed_resolutions': passed_resolutions,
        'delegated_authorities': delegated_authorities,
    }
