"""add unique constraint to phenology_stages

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-25
"""
from alembic import op

revision = "0002"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_phenology_crop_zone_stage",
        "phenology_stages",
        ["crop_id", "agro_zone", "stage_name"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_phenology_crop_zone_stage", "phenology_stages", type_="unique"
    )
