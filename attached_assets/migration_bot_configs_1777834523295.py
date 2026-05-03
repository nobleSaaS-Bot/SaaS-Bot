"""
alembic/versions/xxxx_add_bot_configs.py

Migration: add bot_configs table for multi-tenant bot routing.

Run with:
    alembic upgrade head

To generate a fresh revision file with the proper hash:
    alembic revision --autogenerate -m "add_bot_configs"
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Alembic fills these in during autogenerate
revision = "0001_add_bot_configs"
down_revision = None   # set to your current head
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Enum type ──────────────────────────────────────────────────────────
    bot_status_enum = postgresql.ENUM(
        "pending",
        "active",
        "paused",
        "webhook_failed",
        "revoked",
        name="bot_status_enum",
        create_type=True,
    )
    bot_status_enum.create(op.get_bind(), checkfirst=True)

    # ── Table ──────────────────────────────────────────────────────────────
    op.create_table(
        "bot_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "business_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("businesses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("bot_token_encrypted", sa.Text, nullable=False),
        sa.Column("bot_username", sa.String(64), nullable=False),
        sa.Column("bot_display_name", sa.String(128), nullable=True),
        sa.Column("telegram_bot_id", sa.String(32), nullable=False, unique=True),
        sa.Column(
            "webhook_secret",
            sa.String(64),
            nullable=False,
            unique=True,
        ),
        sa.Column("registered_webhook_url", sa.Text, nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "pending", "active", "paused", "webhook_failed", "revoked",
                name="bot_status_enum",
                create_type=False,
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("is_primary", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("last_webhook_error", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.Column("webhook_registered_at", sa.DateTime, nullable=True),
    )

    # ── Indexes ────────────────────────────────────────────────────────────
    op.create_index(
        "ix_bot_configs_business_id",
        "bot_configs",
        ["business_id"],
    )
    op.create_index(
        "ix_bot_configs_webhook_secret",
        "bot_configs",
        ["webhook_secret"],
        unique=True,
    )
    op.create_index(
        "ix_bot_configs_bot_username",
        "bot_configs",
        ["bot_username"],
    )
    op.create_index(
        "ix_bot_configs_business_status",
        "bot_configs",
        ["business_id", "status"],
    )

    # ── Unique constraint ─────────────────────────────────────────────────
    op.create_unique_constraint(
        "uq_business_telegram_bot",
        "bot_configs",
        ["business_id", "telegram_bot_id"],
    )


def downgrade() -> None:
    op.drop_table("bot_configs")
    op.execute("DROP TYPE IF EXISTS bot_status_enum")
