"""add timestamp mark to heartbeat

Revision ID: 4a1ce83f57dd
Revises: 874e571003f9
Create Date: 2021-04-25 12:11:26.567769

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "4a1ce83f57dd"
down_revision = "874e571003f9"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("heartbeat", sa.Column("mark", sa.Integer(), nullable=True))


def downgrade():
    op.drop_column("heartbeat", "mark")
