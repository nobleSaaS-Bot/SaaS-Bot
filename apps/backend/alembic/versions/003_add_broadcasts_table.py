"""add broadcasts table

Revision ID: 003
Revises: 002
Create Date: 2025-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "broadcasts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("business_id", sa.String(), sa.ForeignKey("businesses.id"), nullable=False),
        sa.Column("store_id", sa.String(), sa.ForeignKey("stores.id"), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("buttons", sa.JSON(), nullable=True),
        sa.Column(
            "segment",
            sa.Enum("all", "new", "regular", "vip", "at_risk", "churned", name="broadcastsegment"),
            nullable=False,
            server_default="all",
        ),
        sa.Column(
            "status",
            sa.Enum("draft", "scheduled", "sending", "sent", "failed", "cancelled", name="broadcaststatus"),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_recipients", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sent_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("delivered_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_broadcasts_business_id", "broadcasts", ["business_id"])
    op.create_index("ix_broadcasts_status", "broadcasts", ["status"])


def downgrade() -> None:
    op.drop_index("ix_broadcasts_status", "broadcasts")
    op.drop_index("ix_broadcasts_business_id", "broadcasts")
    op.drop_table("broadcasts")
    op.execute("DROP TYPE IF EXISTS broadcaststatus")
    op.execute("DROP TYPE IF EXISTS broadcastsegment")
