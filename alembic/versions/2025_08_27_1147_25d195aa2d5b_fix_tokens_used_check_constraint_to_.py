"""fix_tokens_used_check_constraint_to_allow_zero

Revision ID: 25d195aa2d5b
Revises: 2a8f134072cb
Create Date: 2025-08-27 11:47:11.957729+09:00

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "25d195aa2d5b"
down_revision: Union[str, None] = "2a8f134072cb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # tokens_used 체크 제약조건을 > 0에서 >= 0으로 변경 (0 허용)
    op.drop_constraint(
        "ai_usage_logs_tokens_used_check", "ai_usage_logs", type_="check"
    )
    op.create_check_constraint(
        "ai_usage_logs_tokens_used_check", "ai_usage_logs", "tokens_used >= 0"
    )


def downgrade() -> None:
    # 체크 제약조건을 이전 상태로 되돌림 (> 0)
    op.drop_constraint(
        "ai_usage_logs_tokens_used_check", "ai_usage_logs", type_="check"
    )
    op.create_check_constraint(
        "ai_usage_logs_tokens_used_check", "ai_usage_logs", "tokens_used > 0"
    )
