"""Fix missing UUID defaults for all tables

Revision ID: cc5f950d74d7
Revises: d35294aed81e
Create Date: 2025-08-22 10:40:11.447976+09:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cc5f950d74d7'
down_revision: Union[str, None] = 'd35294aed81e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add gen_random_uuid() as default for tables missing UUID defaults
    op.execute("ALTER TABLE email_verifications ALTER COLUMN id SET DEFAULT gen_random_uuid()")
    op.execute("ALTER TABLE fcm_tokens ALTER COLUMN id SET DEFAULT gen_random_uuid()")
    op.execute("ALTER TABLE images ALTER COLUMN id SET DEFAULT gen_random_uuid()")
    op.execute("ALTER TABLE notification_history ALTER COLUMN id SET DEFAULT gen_random_uuid()")
    op.execute("ALTER TABLE notification_settings ALTER COLUMN id SET DEFAULT gen_random_uuid()")
    op.execute("ALTER TABLE notifications ALTER COLUMN id SET DEFAULT gen_random_uuid()")
    op.execute("ALTER TABLE oauth_tokens ALTER COLUMN id SET DEFAULT gen_random_uuid()")
    op.execute("ALTER TABLE password_reset_tokens ALTER COLUMN id SET DEFAULT gen_random_uuid()")
    
    # Update tables still using uuid_generate_v4() to gen_random_uuid()
    op.execute("ALTER TABLE ai_usage_logs ALTER COLUMN id SET DEFAULT gen_random_uuid()")
    op.execute("ALTER TABLE emotion_stats ALTER COLUMN id SET DEFAULT gen_random_uuid()")


def downgrade() -> None:
    # Remove UUID defaults (rollback to previous state)
    op.execute("ALTER TABLE email_verifications ALTER COLUMN id DROP DEFAULT")
    op.execute("ALTER TABLE fcm_tokens ALTER COLUMN id DROP DEFAULT")
    op.execute("ALTER TABLE images ALTER COLUMN id DROP DEFAULT")
    op.execute("ALTER TABLE notification_history ALTER COLUMN id DROP DEFAULT")
    op.execute("ALTER TABLE notification_settings ALTER COLUMN id DROP DEFAULT")
    op.execute("ALTER TABLE notifications ALTER COLUMN id DROP DEFAULT")
    op.execute("ALTER TABLE oauth_tokens ALTER COLUMN id DROP DEFAULT")
    op.execute("ALTER TABLE password_reset_tokens ALTER COLUMN id DROP DEFAULT")
    
    # Restore uuid_generate_v4() for tables that had it
    op.execute("ALTER TABLE ai_usage_logs ALTER COLUMN id SET DEFAULT uuid_generate_v4()")
    op.execute("ALTER TABLE emotion_stats ALTER COLUMN id SET DEFAULT uuid_generate_v4()")