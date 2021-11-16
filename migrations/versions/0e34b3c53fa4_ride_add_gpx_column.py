"""ride add gpx column

Revision ID: 0e34b3c53fa4
Revises: b6ff6a01eca6
Create Date: 2021-11-16 12:57:49.624301

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0e34b3c53fa4"
down_revision = "b6ff6a01eca6"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("ride", sa.Column("gpx", sa.JSON(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("ride", "gpx")
    # ### end Alembic commands ###
