from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, require_action
from app.db.session import get_db
from app.models.entities import CSTMember, GovernanceCommittee, GovernanceResolution, GovernanceVote, AuthorityDelegation, Professional
from app.schemas.api import ApiList, CSTMemberCreate, CSTMemberOut, GovernanceCommitteeCreate, GovernanceCommitteeOut, GovernanceResolutionCreate, GovernanceResolutionOut, GovernanceVoteCreate, GovernanceVoteOut, GovernanceDashboard
from app.services.governance import build_governance_dashboard
from app.services.audit import record_audit
from app.services.events import publish_event

router = APIRouter(prefix='/governance', tags=['governance'])

@router.get('/dashboard', response_model=GovernanceDashboard)
def dashboard(db: Session = Depends(get_db), current_user: Professional = Depends(require_action('governance:read'))):
    return build_governance_dashboard(db)

@router.get('/members', response_model=ApiList)
def list_members(db: Session = Depends(get_db), current_user: Professional = Depends(require_action('governance:read'))):
    items = db.query(CSTMember).filter(CSTMember.is_deleted.is_(False)).order_by(CSTMember.id.desc()).all()
    return {'items': [CSTMemberOut.model_validate(x).model_dump() for x in items], 'total': len(items)}

@router.post('/members', response_model=CSTMemberOut)
def create_member(payload: CSTMemberCreate, db: Session = Depends(get_db), current_user: Professional = Depends(require_action('governance:write'))):
    item = CSTMember(**payload.model_dump())
    db.add(item); db.commit(); db.refresh(item)
    publish_event(db, 'GOVERNANCE.CST_MEMBER_APPOINTED', {'professional_id': item.professional_id})
    record_audit(db, current_user.email, 'GOVERNANCE_MEMBER_CREATE', f'Appointed CST member {item.professional_id}')
    return item

@router.get('/committees', response_model=ApiList)
def list_committees(db: Session = Depends(get_db), current_user: Professional = Depends(require_action('governance:read'))):
    items = db.query(GovernanceCommittee).filter(GovernanceCommittee.is_deleted.is_(False)).order_by(GovernanceCommittee.id.desc()).all()
    return {'items': [GovernanceCommitteeOut.model_validate(x).model_dump() for x in items], 'total': len(items)}

@router.post('/committees', response_model=GovernanceCommitteeOut)
def create_committee(payload: GovernanceCommitteeCreate, db: Session = Depends(get_db), current_user: Professional = Depends(require_action('governance:write'))):
    item = GovernanceCommittee(**payload.model_dump())
    db.add(item); db.commit(); db.refresh(item)
    publish_event(db, 'GOVERNANCE.COMMITTEE_CREATED', {'committee_code': item.code})
    record_audit(db, current_user.email, 'GOVERNANCE_COMMITTEE_CREATE', f'Created committee {item.code}')
    return item

@router.get('/resolutions', response_model=ApiList)
def list_resolutions(db: Session = Depends(get_db), current_user: Professional = Depends(require_action('governance:read'))):
    items = db.query(GovernanceResolution).filter(GovernanceResolution.is_deleted.is_(False)).order_by(GovernanceResolution.id.desc()).all()
    return {'items': [GovernanceResolutionOut.model_validate(x).model_dump() for x in items], 'total': len(items)}

@router.post('/resolutions', response_model=GovernanceResolutionOut)
def create_resolution(payload: GovernanceResolutionCreate, db: Session = Depends(get_db), current_user: Professional = Depends(require_action('governance:write'))):
    data = payload.model_dump(); data['issued_by'] = current_user.id
    item = GovernanceResolution(**data)
    db.add(item); db.commit(); db.refresh(item)
    publish_event(db, 'GOVERNANCE.RESOLUTION_CREATED', {'resolution_uid': item.resolution_uid})
    record_audit(db, current_user.email, 'GOVERNANCE_RESOLUTION_CREATE', f'Created resolution {item.resolution_uid}')
    return item

@router.post('/votes', response_model=GovernanceVoteOut)
def cast_vote(payload: GovernanceVoteCreate, db: Session = Depends(get_db), current_user: Professional = Depends(get_current_user)):
    member = db.query(CSTMember).filter(CSTMember.professional_id == current_user.id, CSTMember.status == 'active', CSTMember.is_deleted.is_(False)).first()
    if not member:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail='User is not an active CST member')
    item = GovernanceVote(resolution_uid=payload.resolution_uid, member_professional_id=current_user.id, vote=payload.vote, rationale=payload.rationale)
    db.add(item); db.commit(); db.refresh(item)
    resolution = db.query(GovernanceResolution).filter(GovernanceResolution.resolution_uid == payload.resolution_uid).first()
    if resolution:
        votes = db.query(GovernanceVote).filter(GovernanceVote.resolution_uid == payload.resolution_uid).all()
        yes = len([v for v in votes if v.vote == 'yes'])
        no = len([v for v in votes if v.vote == 'no'])
        if yes >= 2 and yes > no:
            resolution.status = 'passed'
            db.add(resolution); db.commit()
    publish_event(db, 'GOVERNANCE.VOTE_CAST', {'resolution_uid': payload.resolution_uid, 'vote': payload.vote})
    record_audit(db, current_user.email, 'GOVERNANCE_VOTE_CAST', f'Cast vote on {payload.resolution_uid}')
    return item
