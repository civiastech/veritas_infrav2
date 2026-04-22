
from sqlalchemy.orm import Session
from app.domainx.models import (
    WorkflowDefinition, WorkflowState, WorkflowTransition, WorkflowInstance, WorkflowHistory,
    PolicyRule, PolicyEvaluation, FeatureFlag, CountryConfig,
)


class WorkflowService:
    def __init__(self, db: Session):
        self.db = db

    def create_definition(self, **payload):
        obj = self.db.query(WorkflowDefinition).filter_by(code=payload["code"]).one_or_none()
        if obj is None:
            obj = WorkflowDefinition(**payload)
            self.db.add(obj)
        else:
            for k, v in payload.items():
                setattr(obj, k, v)
        self.db.commit(); self.db.refresh(obj)
        return obj

    def add_state(self, **payload):
        obj = WorkflowState(**payload)
        self.db.add(obj); self.db.commit(); self.db.refresh(obj)
        return obj

    def add_transition(self, **payload):
        obj = WorkflowTransition(**payload)
        self.db.add(obj); self.db.commit(); self.db.refresh(obj)
        return obj

    def start_instance(self, **payload):
        obj = WorkflowInstance(**payload)
        self.db.add(obj); self.db.commit(); self.db.refresh(obj)
        hist = WorkflowHistory(instance_id=obj.id, from_state_code=None, to_state_code=obj.current_state_code, action_code="INIT", actor="system")
        self.db.add(hist); self.db.commit()
        return obj

    def apply_transition(self, instance_id: int, action_code: str, actor: str, actor_role: str | None = None):
        instance = self.db.get(WorkflowInstance, instance_id)
        if instance is None:
            raise ValueError("Workflow instance not found")
        transitions = (
            self.db.query(WorkflowTransition)
            .join(WorkflowDefinition, WorkflowTransition.workflow_id == WorkflowDefinition.id)
            .filter(
                WorkflowDefinition.code == instance.workflow_code,
                WorkflowTransition.from_state_code == instance.current_state_code,
                WorkflowTransition.action_code == action_code,
            )
            .all()
        )
        if not transitions:
            raise ValueError("No matching transition")
        matched = None
        for transition in transitions:
            if transition.required_role is None or transition.required_role == actor_role:
                matched = transition
                break
        if matched is None:
            raise PermissionError("Role not allowed for transition")
        previous = instance.current_state_code
        instance.current_state_code = matched.to_state_code
        self.db.add(instance); self.db.commit(); self.db.refresh(instance)
        hist = WorkflowHistory(instance_id=instance.id, from_state_code=previous, to_state_code=matched.to_state_code, action_code=action_code, actor=actor)
        self.db.add(hist); self.db.commit()
        return instance


class PolicyService:
    def __init__(self, db: Session):
        self.db = db

    def add_rule(self, **payload):
        obj = self.db.query(PolicyRule).filter_by(code=payload["code"]).one_or_none()
        if obj is None:
            obj = PolicyRule(**payload)
            self.db.add(obj)
        else:
            for k, v in payload.items():
                setattr(obj, k, v)
        self.db.commit(); self.db.refresh(obj)
        return obj

    def evaluate(self, **payload):
        rules = self.db.query(PolicyRule).filter(
            PolicyRule.is_active.is_(True),
            PolicyRule.action == payload["action"],
            PolicyRule.resource == payload["resource"],
        ).all()
        matched = None
        decision = "deny"
        rationale = "No matching rule"
        for rule in rules:
            if rule.subject_role and rule.subject_role != payload.get("subject_role"):
                continue
            if rule.country_code and rule.country_code != payload.get("country_code"):
                continue
            if rule.tenant_code and rule.tenant_code != payload.get("tenant_code"):
                continue
            matched = rule
            decision = rule.effect
            rationale = f"Matched rule {rule.code}"
            break
        obj = PolicyEvaluation(**payload, decision=decision, matched_rule=matched.code if matched else None, rationale=rationale)
        self.db.add(obj); self.db.commit(); self.db.refresh(obj)
        return obj


class PlatformConfigService:
    def __init__(self, db: Session):
        self.db = db

    def set_flag(self, **payload):
        obj = self.db.query(FeatureFlag).filter_by(
            code=payload["code"],
            environment=payload.get("environment"),
            tenant_code=payload.get("tenant_code"),
            country_code=payload.get("country_code"),
        ).first()
        if obj is None:
            obj = FeatureFlag(**payload)
        else:
            for k, v in payload.items():
                setattr(obj, k, v)
        self.db.add(obj); self.db.commit(); self.db.refresh(obj)
        return obj

    def is_enabled(self, code: str, environment: str | None = None, tenant_code: str | None = None, country_code: str | None = None):
        flags = self.db.query(FeatureFlag).filter(FeatureFlag.code == code).all()
        for flag in flags:
            if flag.environment and flag.environment != environment:
                continue
            if flag.tenant_code and flag.tenant_code != tenant_code:
                continue
            if flag.country_code and flag.country_code != country_code:
                continue
            return flag.enabled
        return False

    def set_country_config(self, country_code: str, **payload):
        obj = self.db.query(CountryConfig).filter_by(country_code=country_code).first()
        if obj is None:
            obj = CountryConfig(country_code=country_code)
        for k, v in payload.items():
            if hasattr(obj, k):
                setattr(obj, k, v)
        self.db.add(obj); self.db.commit(); self.db.refresh(obj)
        return obj
