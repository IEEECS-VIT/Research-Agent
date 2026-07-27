"""add document doi

Revision ID: b7d1f4d2a9c8
Revises: 80df60883bf8
Create Date: 2026-07-27 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b7d1f4d2a9c8"
down_revision: Union[str, Sequence[str], None] = "80df60883bf8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("doi", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("documents", "doi")