"""initial data

Revision ID: 1f1244f19928
Revises: acc54e65be2a
Create Date: 2021-04-23 22:15:25.440414

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column

# revision identifiers, used by Alembic.
revision = "1f1244f19928"
down_revision = "acc54e65be2a"
branch_labels = None
depends_on = None


def upgrade():

    bike_table = table(
        "bike",
        sa.Column("bike_uuid", sa.String(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False),
        sa.Column("last_status", sa.JSON(), nullable=True),
    )

    op.bulk_insert(
        bike_table,
        [
            {
                "bike_uuid": "8933f238-5ebc-43a7-acc8-2d7272a5e81d",
                "name": "Debug Virtual",
                "config": {
                    "virtual": True,
                    "rm": {
                        "lower_bound": 100,
                        "upper_bound": 3800,
                        "pwm_level": 75,
                        "settled_threshold": 30,
                        "sweep_delay": 0.006,
                        "explicit_targets": [
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                        ],
                    },
                    "rpm": {},
                },
                "is_current": True,
            },
            {
                "bike_uuid": "6e063089-438e-4a9b-a369-9db7bcf9a502",
                "name": "Debug Servo",
                "config": {
                    "virtual": False,
                    "rm": {
                        "lower_bound": 100,
                        "upper_bound": 3800,
                        "pwm_level": 60,
                        "settled_threshold": 10,
                        "sweep_delay": 0.006,
                        "explicit_targets": [
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                        ],
                    },
                    "rpm": {},
                },
                "is_current": False,
            },
            {
                "bike_uuid": "998ac153-f8be-436a-a1ca-4ec14874b181",
                "name": "LifeCycle C1",
                "config": {
                    "virtual": False,
                    "rm": {
                        "lower_bound": 897,
                        "upper_bound": 3773,
                        "pwm_level": 75,
                        "settled_threshold": 10,
                        "sweep_delay": 0.04,
                        "explicit_targets": [
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                        ],
                    },
                    "rpm": {},
                },
                "is_current": False,
            },
        ],
    )


def downgrade():

    op.execute(
        """
        delete from bike
        where bike_uuid in (
            '8933f238-5ebc-43a7-acc8-2d7272a5e81d','6e063089-438e-4a9b-a369-9db7bcf9a502','998ac153-f8be-436a-a1ca-4ec14874b181'
        )
        """
    )
