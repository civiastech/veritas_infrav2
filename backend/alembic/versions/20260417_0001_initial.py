"""initial

Revision ID: 20260417_0001
Revises: 
Create Date: 2026-04-17
"""
from alembic import op
import sqlalchemy as sa

revision = '20260417_0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('professionals',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('band', sa.String(length=50), nullable=False),
        sa.Column('discipline', sa.String(length=100), nullable=True),
        sa.Column('country', sa.String(length=100), nullable=True),
        sa.Column('projects', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('shi_avg', sa.Float(), nullable=False, server_default='0'),
        sa.Column('pri_score', sa.Float(), nullable=False, server_default='0'),
        sa.Column('role', sa.String(length=50), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('bio', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(op.f('ix_professionals_email'), 'professionals', ['email'], unique=True)
    op.create_index(op.f('ix_professionals_role'), 'professionals', ['role'], unique=False)

    op.create_table('projects',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('uid', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('client', sa.String(length=255), nullable=True),
        sa.Column('country', sa.String(length=100), nullable=True),
        sa.Column('type', sa.String(length=100), nullable=True),
        sa.Column('value', sa.Float(), nullable=False, server_default='0'),
        sa.Column('currency', sa.String(length=10), nullable=False, server_default='USD'),
        sa.Column('phase', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='active'),
        sa.Column('progress', sa.Float(), nullable=False, server_default='0'),
        sa.Column('shi', sa.Float(), nullable=False, server_default='0'),
        sa.Column('started', sa.String(length=30), nullable=True),
        sa.Column('target_completion', sa.String(length=30), nullable=True),
        sa.Column('lead_engineer_id', sa.Integer(), sa.ForeignKey('professionals.id'), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(op.f('ix_projects_uid'), 'projects', ['uid'], unique=True)

    op.create_table('components',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('uid', sa.String(length=120), nullable=False),
        sa.Column('project_uid', sa.String(length=100), nullable=False),
        sa.Column('type', sa.String(length=100), nullable=True),
        sa.Column('spec', sa.String(length=255), nullable=True),
        sa.Column('level', sa.String(length=50), nullable=True),
        sa.Column('grid', sa.String(length=50), nullable=True),
        sa.Column('shi', sa.Float(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('material_batch', sa.String(length=100), nullable=True),
        sa.Column('executed_by', sa.Integer(), sa.ForeignKey('professionals.id'), nullable=True),
        sa.Column('approved_by', sa.Integer(), sa.ForeignKey('professionals.id'), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(op.f('ix_components_uid'), 'components', ['uid'], unique=True)
    op.create_index(op.f('ix_components_project_uid'), 'components', ['project_uid'], unique=False)

    op.create_table('evidence',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('component_uid', sa.String(length=120), nullable=False),
        sa.Column('type', sa.String(length=100), nullable=True),
        sa.Column('images', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('submitted_by', sa.Integer(), sa.ForeignKey('professionals.id'), nullable=True),
        sa.Column('approved_by', sa.Integer(), sa.ForeignKey('professionals.id'), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.String(length=50), nullable=True),
        sa.Column('geo', sa.String(length=120), nullable=True),
        sa.Column('hash', sa.String(length=120), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(op.f('ix_evidence_component_uid'), 'evidence', ['component_uid'], unique=False)

    op.create_table('evidence_assets',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('evidence_id', sa.Integer(), sa.ForeignKey('evidence.id'), nullable=False),
        sa.Column('original_name', sa.String(length=255), nullable=False),
        sa.Column('storage_path', sa.String(length=500), nullable=False),
        sa.Column('content_type', sa.String(length=120), nullable=True),
        sa.Column('sha256', sa.String(length=64), nullable=False),
        sa.Column('size_bytes', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(op.f('ix_evidence_assets_evidence_id'), 'evidence_assets', ['evidence_id'], unique=False)
    op.create_index(op.f('ix_evidence_assets_sha256'), 'evidence_assets', ['sha256'], unique=False)
    op.create_unique_constraint('uq_evidence_assets_storage_path', 'evidence_assets', ['storage_path'])

    for ddl in [
        "CREATE TABLE inspections (id INTEGER PRIMARY KEY, component_uid VARCHAR(120), inspector_id INTEGER, shi FLOAT DEFAULT 0, material_score FLOAT DEFAULT 0, assembly_score FLOAT DEFAULT 0, env_score FLOAT DEFAULT 0, supervision_score FLOAT DEFAULT 0, ai_flags INTEGER DEFAULT 0, reason_tag TEXT, timestamp VARCHAR(50), status VARCHAR(50) DEFAULT 'pending', created_at TIMESTAMP, updated_at TIMESTAMP)",
        "CREATE TABLE milestones (id INTEGER PRIMARY KEY, project_uid VARCHAR(100), name VARCHAR(255), phase INTEGER DEFAULT 1, amount FLOAT DEFAULT 0, currency VARCHAR(10) DEFAULT 'USD', required_shi FLOAT DEFAULT 0, status VARCHAR(50) DEFAULT 'pending', released_date VARCHAR(50), description TEXT, created_at TIMESTAMP, updated_at TIMESTAMP)",
        "CREATE TABLE payments (id INTEGER PRIMARY KEY, project_uid VARCHAR(100), milestone_id INTEGER, amount FLOAT DEFAULT 0, currency VARCHAR(10) DEFAULT 'USD', from_party VARCHAR(255), to_party VARCHAR(255), released_by VARCHAR(255), date VARCHAR(50), tx_id VARCHAR(100), status VARCHAR(50) DEFAULT 'pending', created_at TIMESTAMP, updated_at TIMESTAMP)",
        "CREATE TABLE tenders (id INTEGER PRIMARY KEY, uid VARCHAR(100), name VARCHAR(255), client VARCHAR(255), country VARCHAR(100), value FLOAT DEFAULT 0, currency VARCHAR(10) DEFAULT 'USD', deadline VARCHAR(50), status VARCHAR(50) DEFAULT 'open', type VARCHAR(100), description TEXT, created_at TIMESTAMP, updated_at TIMESTAMP)",
        "CREATE UNIQUE INDEX ix_tenders_uid ON tenders (uid)",
        "CREATE TABLE bids (id INTEGER PRIMARY KEY, tender_uid VARCHAR(100), firm VARCHAR(255), price FLOAT DEFAULT 0, integrity_score FLOAT DEFAULT 0, capacity_score FLOAT DEFAULT 0, shi_history FLOAT DEFAULT 0, matrix_score FLOAT DEFAULT 0, status VARCHAR(50) DEFAULT 'submitted', submitted_by INTEGER, created_at TIMESTAMP, updated_at TIMESTAMP)",
        "CREATE TABLE disputes (id INTEGER PRIMARY KEY, uid VARCHAR(100), project_uid VARCHAR(100), component_uid VARCHAR(120), type VARCHAR(100), raised_by INTEGER, against_party VARCHAR(255), description TEXT, status VARCHAR(50) DEFAULT 'open', resolution TEXT, raised_date VARCHAR(50), resolved_date VARCHAR(50), arbitrator_id INTEGER, created_at TIMESTAMP, updated_at TIMESTAMP)",
        "CREATE UNIQUE INDEX ix_disputes_uid ON disputes (uid)",
        "CREATE TABLE materials (id INTEGER PRIMARY KEY, batch_uid VARCHAR(120), name VARCHAR(255), grade VARCHAR(100), supplier VARCHAR(255), country VARCHAR(100), cert_number VARCHAR(120), verified BOOLEAN DEFAULT false, projects_used JSON, test_strength FLOAT DEFAULT 0, required_strength FLOAT DEFAULT 0, status VARCHAR(50) DEFAULT 'pending', suspension_reason TEXT, created_at TIMESTAMP, updated_at TIMESTAMP)",
        "CREATE UNIQUE INDEX ix_materials_batch_uid ON materials (batch_uid)",
        "CREATE TABLE certifications (id INTEGER PRIMARY KEY, project_uid VARCHAR(100), type VARCHAR(100), shi_composite FLOAT DEFAULT 0, issued_by INTEGER, co_signed_by INTEGER, issued_date VARCHAR(50), physical_plate VARCHAR(120), status VARCHAR(50) DEFAULT 'pending', qr_code VARCHAR(120), notes TEXT, created_at TIMESTAMP, updated_at TIMESTAMP)",
        "CREATE TABLE audit_logs (id INTEGER PRIMARY KEY, action VARCHAR(120), actor VARCHAR(255), detail TEXT, timestamp VARCHAR(50), created_at TIMESTAMP, updated_at TIMESTAMP)",
        "CREATE TABLE sensors (id INTEGER PRIMARY KEY, component_uid VARCHAR(120), type VARCHAR(100), current_reading FLOAT DEFAULT 0, unit VARCHAR(50), threshold FLOAT DEFAULT 0, status VARCHAR(50) DEFAULT 'normal', last_update VARCHAR(50), created_at TIMESTAMP, updated_at TIMESTAMP)",
        "CREATE TABLE notifications (id INTEGER PRIMARY KEY, type VARCHAR(100), message TEXT, priority VARCHAR(50) DEFAULT 'medium', read BOOLEAN DEFAULT false, for_role JSON, created_at TIMESTAMP, updated_at TIMESTAMP)"
    ]:
        op.execute(sa.text(ddl))


def downgrade() -> None:
    for table in ['notifications','sensors','audit_logs','certifications','materials','disputes','bids','tenders','payments','milestones','inspections','evidence_assets','evidence','components','projects','professionals']:
        op.drop_table(table)
