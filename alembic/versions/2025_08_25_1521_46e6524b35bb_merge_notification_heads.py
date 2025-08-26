"""merge_notification_heads

Revision ID: 46e6524b35bb
Revises: cc5f950d74d7, 8dbdae5b349a
Create Date: 2025-08-25 15:21:28.322231+09:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '46e6524b35bb'
down_revision: Union[str, None] = ('cc5f950d74d7', '8dbdae5b349a')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass