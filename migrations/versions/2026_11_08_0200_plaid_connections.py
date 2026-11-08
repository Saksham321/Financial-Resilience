"""Encrypted user-owned Plaid connections."""
from alembic import op
import sqlalchemy as sa
from app.shared.database.base import GUID
revision = 'plaid_connections_v1'
down_revision = 'scheduled_notifications_v1'
branch_labels = None
depends_on = None

def upgrade():
    schema = 'core' if op.get_bind().dialect.name == 'postgresql' else None
    if sa.inspect(op.get_bind()).has_table('plaid_connections', schema=schema):
        return
    op.create_table('plaid_connections',
        sa.Column('id', GUID(), primary_key=True),
        sa.Column('user_id', GUID(), sa.ForeignKey(('core.' if schema else '')+'users.id'), nullable=False),
        sa.Column('item_id', sa.String(150), nullable=False),
        sa.Column('encrypted_access_token', sa.LargeBinary(), nullable=False),
        sa.Column('environment', sa.String(20), nullable=False),
        sa.Column('account_map', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('user_id', 'item_id'), schema=schema)
    op.create_index('ix_plaid_connections_user_id', 'plaid_connections', ['user_id'], schema=schema)

def downgrade():
    op.drop_table('plaid_connections', schema='core' if op.get_bind().dialect.name == 'postgresql' else None)
