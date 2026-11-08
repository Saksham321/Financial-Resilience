"""Persist exact billing reminder due times and cancellation state."""
from alembic import op
import sqlalchemy as sa

revision='scheduled_notifications_v1'
down_revision='raw_datasets_v1'
branch_labels=None
depends_on=None


def upgrade():
    schema='core' if op.get_bind().dialect.name=='postgresql' else None
    columns={c['name'] for c in sa.inspect(op.get_bind()).get_columns('notifications',schema=schema)}
    if 'scheduled_for' not in columns:
        op.add_column('notifications',sa.Column('scheduled_for',sa.DateTime(timezone=True),nullable=True),schema=schema)
    if 'cancelled' not in columns:
        op.add_column('notifications',sa.Column('cancelled',sa.Boolean(),nullable=False,server_default=sa.false()),schema=schema)
    indexes=sa.inspect(op.get_bind()).get_indexes('notifications',schema=schema)
    if not any(i['column_names']==['scheduled_for'] for i in indexes):
        op.create_index('ix_core_notifications_scheduled_for','notifications',['scheduled_for'],schema=schema)


def downgrade():
    schema='core' if op.get_bind().dialect.name=='postgresql' else None
    with op.batch_alter_table('notifications',schema=schema) as batch:
        batch.drop_index('ix_core_notifications_scheduled_for')
        batch.drop_column('cancelled')
        batch.drop_column('scheduled_for')
