
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.entities import PermissionGrant, Project, ProjectAssignment, Professional

ROLE_ACTIONS = {
    "admin": {"*"},
    "engineer": {
        "projects:read", "projects:write",
        "components:read", "components:write",
        "evidence:read", "evidence:write",
        "inspections:read", "inspections:approve",
        "materials:read", "materials:write",
        "monitor:read", "monitor:write",
        "seal:read", "seal:write",
        "pay:read", "pay:write",
        "lex:read", "lex:write",
        "notifications:read",
        "twin:read",
        "atlas:read", "verifund:read", "verifund:write", "academy:read", "academy:write", "clone:read", "clone:write", "governance:read", "governance:write", "regulatory:read", "regulatory:write",
        "prefab:read", "prefab:write", "prefab:approve",
        "ethics:read", "ethics:write",
        "origin:read", "origin:write",
    },
    "inspector": {
        "projects:read", "components:read",
        "evidence:read", "inspections:read", "inspections:approve",
        "monitor:read", "lex:read", "lex:write", "seal:read", "twin:read", "notifications:read", "academy:read", "atlas:read", "governance:read", "regulatory:read", "clone:read",
        "prefab:read", "prefab:write",
        "ethics:read", "ethics:write", "ethics:panel",
        "origin:read", "origin:write", "origin:approve",
    },
    "supervisor": {
        "projects:read", "components:read", "components:write",
        "evidence:read", "evidence:write",
        "monitor:read", "notifications:read", "academy:read", "regulatory:read", "clone:read",
        "prefab:read",
        "ethics:read",
        "origin:read",
    },
    "contractor": {
        "projects:read", "evidence:read", "tenders:read", "notifications:read", "academy:read", "verifund:read", "verifund:write", "clone:read", "prefab:read",
        "ethics:read",
        "origin:read", "origin:write",
    },
}

def ensure_permission(db: Session, user: Professional, action: str, project_uid: str | None = None) -> None:
    role_actions = ROLE_ACTIONS.get(user.role, set())
    if "*" in role_actions or action in role_actions:
        if project_uid and user.role != "admin":
            if user.role == "engineer":
                project = db.query(Project).filter(Project.uid == project_uid).first()
                if project and project.lead_engineer_id == user.id:
                    return
            assignment = db.query(ProjectAssignment).filter(
                ProjectAssignment.project_uid == project_uid,
                ProjectAssignment.professional_id == user.id,
            ).first()
            if assignment:
                if action.endswith(":approve") and not assignment.can_approve:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Approval rights not granted for this project")
                return
            if action.endswith(":read"):
                return
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not assigned to this project")
        return

    grant = db.query(PermissionGrant).filter(
        PermissionGrant.professional_id == user.id,
        PermissionGrant.action == action,
        PermissionGrant.allowed.is_(True),
    ).first()
    if grant and (grant.resource_uid is None or grant.resource_uid == project_uid):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
