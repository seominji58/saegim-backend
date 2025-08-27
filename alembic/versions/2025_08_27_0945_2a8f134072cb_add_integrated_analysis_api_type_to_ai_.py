"""add_integrated_analysis_api_type_to_ai_usage_logs

Revision ID: 2a8f134072cb
Revises: c5a0b25bffdf
Create Date: 2025-08-27 09:45:23.858225+09:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2a8f134072cb'
down_revision: Union[str, None] = 'c5a0b25bffdf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # AI 사용 로그의 api_type 체크 제약조건에 'integrated_analysis' 추가
    op.drop_constraint('ck_ai_usage_api_type', 'ai_usage_logs', type_='check')
    op.create_check_constraint(
        'ck_ai_usage_api_type',
        'ai_usage_logs',
        "api_type IN ('generate', 'keywords', 'emotion_analysis', 'integrated_analysis')"
    )


def downgrade() -> None:
    # 체크 제약조건을 이전 상태로 되돌림
    op.drop_constraint('ck_ai_usage_api_type', 'ai_usage_logs', type_='check')
    op.create_check_constraint(
        'ck_ai_usage_api_type',
        'ai_usage_logs',
        "api_type IN ('generate', 'keywords', 'emotion_analysis')"
    )