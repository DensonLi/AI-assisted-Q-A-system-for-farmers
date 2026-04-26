"""add system_configs table

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-26
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"


def upgrade() -> None:
    op.create_table(
        "system_configs",
        sa.Column("key", sa.String(128), primary_key=True),
        sa.Column("value", sa.Text, nullable=False, server_default=""),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # 写入默认配置项（值留空，由 .env 提供实际值）
    op.execute(
        sa.text("""
        INSERT INTO system_configs (key, value, description) VALUES
        ('knowledge_api_base_url', '', '知识库 API 地址（完整 URL）'),
        ('knowledge_api_key',      '', '知识库 API Key（x-api-key）'),
        ('knowledge_bot_id',       '', '知识库机器人 ID（bot_id）'),
        ('llm_api_key',            '', 'LLM API Key'),
        ('llm_base_url',           '', 'LLM Base URL（OpenAI 兼容接口）'),
        ('llm_model',              '', 'LLM 模型名称')
        ON CONFLICT (key) DO NOTHING;
        """)
    )


def downgrade() -> None:
    op.drop_table("system_configs")
