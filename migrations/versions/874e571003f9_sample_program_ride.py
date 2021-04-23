"""sample program ride

Revision ID: 874e571003f9
Revises: 1f1244f19928
Create Date: 2021-04-23 22:45:03.838874

"""

import datetime

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table


# revision identifiers, used by Alembic.
revision = "874e571003f9"
down_revision = "1f1244f19928"
branch_labels = None
depends_on = None


def upgrade():

    ride_table = table(
        "ride",
        sa.Column("ride_uuid", sa.String(), nullable=False),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("date_start", sa.DateTime(), nullable=False),
        sa.Column("date_end", sa.DateTime(), nullable=True),
        sa.Column("duration", sa.Float(), nullable=False),
        sa.Column("completed", sa.Float(), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False),
        sa.Column("program", sa.JSON(), nullable=True),
    )

    op.bulk_insert(
        ride_table,
        [
            {
                "ride_uuid": "c75a19f7-6650-4430-b979-6a3b627456d1",
                "name": "Boss Program",
                "date_start": datetime.datetime.now(),
                "date_end": None,
                "duration": 60,
                "completed": 0,
                "is_current": False,
                "program": [
                    [4, [0, 10]],
                    [8, [10, 20]],
                    [12, [20, 30]],
                    [3, [30, 40]],
                    [9, [40, 50]],
                    [2, [50, 60]],
                ],
            }
        ],
    )


def downgrade():

    op.execute(
        """
        delete from ride where ride_uuid = 'c75a19f7-6650-4430-b979-6a3b627456d1';
        """
    )
