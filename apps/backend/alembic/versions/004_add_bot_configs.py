"""
alembic/versions/004_add_bot_configs.py

Migration: add bot_configs table for multi-tenant bot routing.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:

    op.create_table(
        "bot_configs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "business_id",
            sa.String(),
            sa.ForeignKey("businesses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("bot_token_encrypted", sa.Text, nullable=False),
        sa.Column("bot_username", sa.String(64), nullable=False),
        sa.Column("bot_display_name", sa.String(128), nullable=True),
        sa.Column("telegram_bot_id", sa.String(32), nullable=False, unique=True),
        sa.Column("webhook_secret", sa.String(64), nullable=False, unique=True),
        sa.Column("registered_webhook_url", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("is_primary", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("last_webhook_error", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("webhook_registered_at", sa.DateTime, nullable=True),
    )

    op.create_index("ix_bot_configs_business_id", "bot_configs", ["business_id"])
    op.create_index("ix_bot_configs_webhook_secret", "bot_configs", ["webhook_secret"], unique=True)
    op.create_index("ix_bot_configs_bot_username", "bot_configs", ["bot_username"])
    op.create_index("ix_bot_configs_business_status", "bot_configs", ["business_id", "status"])
    op.create_unique_constraint("uq_business_telegram_bot", "bot_configs", ["business_id", "telegram_bot_id"])


def downgrade() -> None:
    op.drop_table("bot_configs")
    op.execute("DROP TYPE IF EXISTS bot_status_enum")
