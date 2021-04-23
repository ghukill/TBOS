"""first migration

Revision ID: acc54e65be2a
Revises: 
Create Date: 2021-04-23 22:13:43.507895

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "acc54e65be2a"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "bike",
        sa.Column("bike_uuid", sa.String(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False),
        sa.Column("last_status", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("bike_uuid"),
    )
    op.create_table(
        "pyb_job_queue",
        sa.Column("job_uuid", sa.String(), nullable=False),
        sa.Column("timestamp_added", sa.Integer(), nullable=False),
        sa.Column("cmds", sa.JSON(), nullable=False),
        sa.Column("resps", sa.JSON(), nullable=True),
        sa.Column("resp_idx", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("job_uuid"),
    )
    op.create_table(
        "ride",
        sa.Column("ride_uuid", sa.String(), nullable=False),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("date_start", sa.DateTime(), nullable=False),
        sa.Column("date_end", sa.DateTime(), nullable=True),
        sa.Column("duration", sa.Float(), nullable=False),
        sa.Column("completed", sa.Float(), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False),
        sa.Column("program", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("ride_uuid"),
    )
    op.create_table(
        "heartbeat",
        sa.Column("hb_uuid", sa.String(), nullable=False),
        sa.Column("timestamp_added", sa.Integer(), nullable=False),
        sa.Column("ride_uuid", sa.String(), nullable=True),
        sa.Column("data", sa.JSON(), nullable=True),
        sa.Column("level", sa.Integer(), nullable=True),
        sa.Column("rpm", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(
            ["ride_uuid"],
            ["ride.ride_uuid"],
        ),
        sa.PrimaryKeyConstraint("hb_uuid"),
    )

    # create unique index
    op.execute(
        """
        create unique index if not exists
        pyb_job_running_idx on pyb_job_queue (status)
        where status = 'running'
    """
    )


def downgrade():
    op.drop_table("heartbeat")
    op.drop_table("ride")
    op.drop_table("pyb_job_queue")
    op.drop_table("bike")
