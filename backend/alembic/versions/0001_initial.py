"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-04-25

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # users
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("username", sa.String(64), nullable=False),
        sa.Column("email", sa.String(256), nullable=False),
        sa.Column("hashed_password", sa.String(256), nullable=False),
        sa.Column("role", sa.Enum("admin", "user", name="userrole"), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("default_region_id", sa.Integer, nullable=True),
        sa.Column("favorite_crop_codes", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("username"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_username", "users", ["username"])
    op.create_index("ix_users_email", "users", ["email"])

    # regions
    op.create_table(
        "regions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("code", sa.String(12), nullable=False, unique=True),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("full_name", sa.String(256), nullable=False),
        sa.Column("level", sa.SmallInteger, nullable=False),
        sa.Column("parent_id", sa.Integer, sa.ForeignKey("regions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("agro_zone", sa.String(32), nullable=True),
    )
    op.create_index("ix_regions_code", "regions", ["code"])
    op.create_index("ix_regions_parent_id", "regions", ["parent_id"])
    op.create_index("ix_regions_agro_zone", "regions", ["agro_zone"])
    op.create_index("ix_regions_level_parent", "regions", ["level", "parent_id"])

    # crops
    op.create_table(
        "crops",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("code", sa.String(32), nullable=False, unique=True),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("category", sa.String(16), nullable=False),
        sa.Column("parent_id", sa.Integer, sa.ForeignKey("crops.id", ondelete="SET NULL"), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("aliases", postgresql.JSONB, nullable=True),
    )
    op.create_index("ix_crops_code", "crops", ["code"])
    op.create_index("ix_crops_category", "crops", ["category"])

    # phenology_stages
    op.create_table(
        "phenology_stages",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("crop_id", sa.Integer, sa.ForeignKey("crops.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agro_zone", sa.String(32), nullable=False),
        sa.Column("stage_name", sa.String(64), nullable=False),
        sa.Column("start_month", sa.SmallInteger, nullable=False),
        sa.Column("start_day", sa.SmallInteger, nullable=False, server_default="1"),
        sa.Column("end_month", sa.SmallInteger, nullable=False),
        sa.Column("end_day", sa.SmallInteger, nullable=False, server_default="31"),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("key_activities", postgresql.JSONB, nullable=True),
    )
    op.create_index("ix_phenology_crop_id", "phenology_stages", ["crop_id"])
    op.create_index("ix_phenology_agro_zone", "phenology_stages", ["agro_zone"])

    # conversations
    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("region_id", sa.Integer, sa.ForeignKey("regions.id"), nullable=True),
        sa.Column("crop_id", sa.Integer, sa.ForeignKey("crops.id"), nullable=True),
        sa.Column("title", sa.String(256), nullable=False, server_default="新对话"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # messages
    op.create_table(
        "messages",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("conversation_id", sa.Integer, sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])

    # user_crop_memories
    op.create_table(
        "user_crop_memories",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("region_id", sa.Integer, sa.ForeignKey("regions.id"), nullable=False),
        sa.Column("crop_id", sa.Integer, sa.ForeignKey("crops.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "region_id", "crop_id", name="uq_user_region_crop"),
    )

    # memory_items
    op.create_table(
        "memory_items",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("memory_id", sa.Integer, sa.ForeignKey("user_crop_memories.id", ondelete="CASCADE"), nullable=False),
        sa.Column("key", sa.String(64), nullable=False),
        sa.Column("value", sa.Text, nullable=False),
        sa.Column("confidence", sa.Float, nullable=False, server_default="1.0"),
        sa.Column("source", sa.String(32), nullable=False, server_default="user_confirmed"),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_memory_items_memory_id", "memory_items", ["memory_id"])
    op.create_index("ix_memory_items_key", "memory_items", ["key"])
    op.create_index("ix_memory_items_status", "memory_items", ["status"])

    # memory_update_proposals
    op.create_table(
        "memory_update_proposals",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("memory_id", sa.Integer, sa.ForeignKey("user_crop_memories.id", ondelete="CASCADE"), nullable=False),
        sa.Column("conversation_id", sa.Integer, sa.ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(16), nullable=False),
        sa.Column("target_item_id", sa.Integer, sa.ForeignKey("memory_items.id", ondelete="SET NULL"), nullable=True),
        sa.Column("proposed_key", sa.String(64), nullable=False),
        sa.Column("proposed_value", sa.Text, nullable=False),
        sa.Column("confidence", sa.Float, nullable=False, server_default="0.7"),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_proposals_memory_id", "memory_update_proposals", ["memory_id"])
    op.create_index("ix_proposals_status", "memory_update_proposals", ["status"])


def downgrade() -> None:
    op.drop_table("memory_update_proposals")
    op.drop_table("memory_items")
    op.drop_table("user_crop_memories")
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("phenology_stages")
    op.drop_table("crops")
    op.drop_table("regions")
    op.drop_table("users")
    sa.Enum(name="userrole").drop(op.get_bind(), checkfirst=True)
