"""add workflow policy platform config

Revision ID: 20260417_0003
Revises: 20260417_0002
Create Date: 2026-04-17
"""
from alembic import op
import sqlalchemy as sa

revision = '20260417_0003'
down_revision = '20260417_0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('workflow_definitions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('code', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('country_code', sa.String(length=20), nullable=True),
        sa.Column('tenant_code', sa.String(length=100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_workflow_definitions_code', 'workflow_definitions', ['code'], unique=True)

    op.create_table('workflow_states',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('workflow_id', sa.Integer(), sa.ForeignKey('workflow_definitions.id'), nullable=False),
        sa.Column('code', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('is_initial', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('is_terminal', sa.Boolean(), nullable=False, server_default=sa.text('false')),
    )
    op.create_table('workflow_transitions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('workflow_id', sa.Integer(), sa.ForeignKey('workflow_definitions.id'), nullable=False),
        sa.Column('from_state_code', sa.String(length=100), nullable=False),
        sa.Column('to_state_code', sa.String(length=100), nullable=False),
        sa.Column('action_code', sa.String(length=100), nullable=False),
        sa.Column('required_role', sa.String(length=100), nullable=True),
        sa.Column('condition_expr', sa.Text(), nullable=True),
    )
    op.create_table('workflow_instances',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('workflow_code', sa.String(length=100), nullable=False),
        sa.Column('entity_type', sa.String(length=100), nullable=False),
        sa.Column('entity_id', sa.String(length=100), nullable=False),
        sa.Column('current_state_code', sa.String(length=100), nullable=False),
        sa.Column('country_code', sa.String(length=20), nullable=True),
        sa.Column('tenant_code', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table('workflow_history',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('instance_id', sa.Integer(), sa.ForeignKey('workflow_instances.id'), nullable=False),
        sa.Column('from_state_code', sa.String(length=100), nullable=True),
        sa.Column('to_state_code', sa.String(length=100), nullable=False),
        sa.Column('action_code', sa.String(length=100), nullable=False),
        sa.Column('actor', sa.String(length=200), nullable=False),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table('policy_rules',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('code', sa.String(length=100), nullable=False),
        sa.Column('subject_role', sa.String(length=100), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('resource', sa.String(length=100), nullable=False),
        sa.Column('country_code', sa.String(length=20), nullable=True),
        sa.Column('tenant_code', sa.String(length=100), nullable=True),
        sa.Column('effect', sa.String(length=20), nullable=False),
        sa.Column('condition_expr', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_policy_rules_code', 'policy_rules', ['code'], unique=True)
    op.create_table('policy_evaluations',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('subject', sa.String(length=200), nullable=False),
        sa.Column('subject_role', sa.String(length=100), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('resource', sa.String(length=100), nullable=False),
        sa.Column('country_code', sa.String(length=20), nullable=True),
        sa.Column('tenant_code', sa.String(length=100), nullable=True),
        sa.Column('decision', sa.String(length=20), nullable=False),
        sa.Column('matched_rule', sa.String(length=100), nullable=True),
        sa.Column('rationale', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table('feature_flags',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('code', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('environment', sa.String(length=50), nullable=True),
        sa.Column('tenant_code', sa.String(length=100), nullable=True),
        sa.Column('country_code', sa.String(length=20), nullable=True),
        sa.Column('stability', sa.String(length=20), nullable=False, server_default='stable'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_feature_flags_code', 'feature_flags', ['code'])
    op.create_table('country_configs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('country_code', sa.String(length=20), nullable=False),
        sa.Column('default_workflow_variant', sa.String(length=100), nullable=True),
        sa.Column('certification_rule', sa.String(length=100), nullable=True),
        sa.Column('payment_rule', sa.String(length=100), nullable=True),
        sa.Column('evidence_rule', sa.String(length=100), nullable=True),
        sa.Column('regulator_override', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('config_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_country_configs_country_code', 'country_configs', ['country_code'], unique=True)


def downgrade() -> None:
    pass
