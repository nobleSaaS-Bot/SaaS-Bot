"""add customers table

Revision ID: 002
Revises: 001
Create Date: 2025-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("business_id", sa.String(), sa.ForeignKey("businesses.id"), nullable=False),
        sa.Column("store_id", sa.String(), sa.ForeignKey("stores.id"), nullable=True),
        sa.Column("telegram_id", sa.String(100), nullable=False),
        sa.Column("first_name", sa.String(100), nullable=True),
        sa.Column("last_name", sa.String(100), nullable=True),
        sa.Column("username", sa.String(100), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("language_code", sa.String(10), nullable=True),
        sa.Column("photo_url", sa.Text(), nullable=True),
        sa.Column(
            "segment",
            sa.Enum("new", "regular", "vip", "at_risk", "churned", name="customersegment"),
            nullable=False,
            server_default="new",
        ),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("total_orders", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_spent", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(10), nullable=False, server_default="USD"),
        sa.Column("last_order_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_blocked", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_customers_business_id", "customers", ["business_id"])
    op.create_index("ix_customers_telegram_id", "customers", ["telegram_id"])
    op.create_index("ix_customers_segment", "customers", ["segment"])


def downgrade() -> None:
    op.drop_index("ix_customers_segment", "customers")
    op.drop_index("ix_customers_telegram_id", "customers")
    op.drop_index("ix_customers_business_id", "customers")
    op.drop_table("customers")
    op.execute("DROP TYPE IF EXISTS customersegment")
