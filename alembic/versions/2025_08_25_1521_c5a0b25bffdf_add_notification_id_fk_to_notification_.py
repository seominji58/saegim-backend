"""add_notification_id_fk_to_notification_history

Revision ID: c5a0b25bffdf
Revises: 46e6524b35bb
Create Date: 2025-08-25 15:21:33.148118+09:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "c5a0b25bffdf"
down_revision: Union[str, None] = "46e6524b35bb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. notification_history 테이블에 notification_id 컬럼 추가
    op.add_column(
        "notification_history",
        sa.Column("notification_id", postgresql.UUID(), nullable=True),
    )

    # 2. notification_id에 대한 외래 키 제약 조건 추가
    op.create_foreign_key(
        "fk_notification_history_notification_id",
        "notification_history",
        "notifications",
        ["notification_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # 3. notification_id에 인덱스 추가
    op.create_index(
        "idx_notification_history_notification_id",
        "notification_history",
        ["notification_id"],
    )

    # 4. 중복 필드 제거 (title, body)
    # 주의: 기존 데이터 마이그레이션 필요
    # 실제 환경에서는 데이터 백업 후 진행
    op.drop_column("notification_history", "title")
    op.drop_column("notification_history", "body")


def downgrade() -> None:
    # 1. 제거했던 컬럼들 다시 추가
    op.add_column(
        "notification_history",
        sa.Column("title", sa.VARCHAR(length=255), nullable=False),
    )
    op.add_column(
        "notification_history",
        sa.Column("body", sa.VARCHAR(length=1000), nullable=False),
    )

    # 2. 인덱스 제거
    op.drop_index(
        "idx_notification_history_notification_id", table_name="notification_history"
    )

    # 3. 외래 키 제약 조건 제거
    op.drop_constraint(
        "fk_notification_history_notification_id",
        "notification_history",
        type_="foreignkey",
    )

    # 4. notification_id 컬럼 제거
    op.drop_column("notification_history", "notification_id")
