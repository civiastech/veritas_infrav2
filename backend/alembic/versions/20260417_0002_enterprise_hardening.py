"""enterprise hardening

Revision ID: 20260417_0002
Revises: 20260417_0001
Create Date: 2026-04-17
"""
from alembic import op
import sqlalchemy as sa

revision = '20260417_0002'
down_revision = '20260417_0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # professionals
    op.add_column('professionals', sa.Column('is_deleted', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.add_column('professionals', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('professionals', sa.Column('mfa_enabled', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.add_column('professionals', sa.Column('mfa_secret', sa.String(length=64), nullable=True))
    op.add_column('professionals', sa.Column('failed_login_attempts', sa.Integer(), server_default='0', nullable=False))
    op.add_column('professionals', sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True))

    for table in ['projects','components','evidence','inspections','milestones','payments','tenders','bids','disputes','materials','certifications','sensors','notifications']:
        op.add_column(table, sa.Column('is_deleted', sa.Boolean(), server_default=sa.text('false'), nullable=False))
        op.add_column(table, sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))

    op.add_column('evidence_assets', sa.Column('storage_backend', sa.String(length=50), server_default='filesystem', nullable=False))
    op.add_column('evidence_assets', sa.Column('immutable', sa.Boolean(), server_default=sa.text('true'), nullable=False))

    op.add_column('audit_logs', sa.Column('ip_address', sa.String(length=64), nullable=True))
    op.add_column('audit_logs', sa.Column('route', sa.String(length=255), nullable=True))
    op.add_column('audit_logs', sa.Column('immutable', sa.Boolean(), server_default=sa.text('true'), nullable=False))

    op.create_table('project_assignments',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('project_uid', sa.String(length=100), nullable=False),
        sa.Column('professional_id', sa.Integer(), sa.ForeignKey('professionals.id'), nullable=False),
        sa.Column('role_on_project', sa.String(length=50), nullable=False, server_default='viewer'),
        sa.Column('can_approve', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_project_assignments_project_uid', 'project_assignments', ['project_uid'])
    op.create_index('ix_project_assignments_professional_id', 'project_assignments', ['professional_id'])

    op.create_table('permission_grants',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('professional_id', sa.Integer(), sa.ForeignKey('professionals.id'), nullable=False),
        sa.Column('resource_type', sa.String(length=100), nullable=False),
        sa.Column('resource_uid', sa.String(length=120), nullable=True),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('allowed', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table('refresh_tokens',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('token_id', sa.String(length=64), nullable=False),
        sa.Column('professional_id', sa.Integer(), sa.ForeignKey('professionals.id'), nullable=False),
        sa.Column('revoked', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_refresh_tokens_token_id', 'refresh_tokens', ['token_id'], unique=True)
    op.create_index('ix_refresh_tokens_professional_id', 'refresh_tokens', ['professional_id'])

    op.create_table('auth_attempts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('ip_address', sa.String(length=64), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('reason', sa.String(length=120), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_auth_attempts_email', 'auth_attempts', ['email'])

    op.create_table('event_logs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('event_type', sa.String(length=120), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_event_logs_event_type', 'event_logs', ['event_type'])


def downgrade() -> None:
    pass
