"""add reminders table

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-26
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"


def upgrade() -> None:
    op.create_table(
        "reminders",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("conversation_id", sa.Integer, sa.ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("region_id", sa.Integer, sa.ForeignKey("regions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("crop_id", sa.Integer, sa.ForeignKey("crops.id", ondelete="SET NULL"), nullable=True),
        sa.Column("scheduled_date", sa.Date, nullable=False),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("task_description", sa.Text, nullable=False, server_default=""),
        sa.Column("operation_steps", sa.Text, nullable=False, server_default=""),
        sa.Column("key_notes", sa.Text, nullable=False, server_default=""),
        sa.Column("is_done", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_reminders_user_date", "reminders", ["user_id", "scheduled_date"])


def downgrade() -> None:
    op.drop_index("ix_reminders_user_date", table_name="reminders")
    op.drop_table("reminders")
