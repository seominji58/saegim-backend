"""remove_verified_at_column

Revision ID: 8dbdae5b349a
Revises: change_email_verification_to_is_used
Create Date: 2025-08-22 10:56:26.573995+09:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8dbdae5b349a'
down_revision: Union[str, None] = 'change_email_to_is_used'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # email_verifications 테이블에서 verified_at 컬럼만 제거
    op.drop_column('email_verifications', 'verified_at')


def downgrade() -> None:
    # 롤백 시 verified_at 컬럼 다시 추가
    op.add_column('email_verifications', sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True))