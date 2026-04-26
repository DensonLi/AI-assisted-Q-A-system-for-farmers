"""
自定义 SQLAlchemy 类型：
  - PostgreSQL 生产环境使用原生 JSONB
  - SQLite 测试环境自动降级为 JSON
"""
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB as _PgJSONB
from sqlalchemy.types import TypeDecorator


class JSONB(TypeDecorator):
    """方言自适应 JSONB：PostgreSQL → JSONB，其他 → JSON"""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(_PgJSONB())
        return dialect.type_descriptor(JSON())

    def process_bind_param(self, value, dialect):
        return value

    def process_result_value(self, value, dialect):
        return value
