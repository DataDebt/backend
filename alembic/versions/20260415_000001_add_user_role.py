"""add user role column

Revision ID: 20260415_add_user_role
Revises: 20260409_create_auth_tables
Create Date: 2026-04-15 00:00:01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260415_add_user_role"
down_revision: Union[str, Sequence[str], None] = "20260409_create_auth_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("role", sa.String(20), nullable=False, server_default="user"),
    )
    op.create_check_constraint(
        "ck_users_role",
        "users",
        "role IN ('user', 'admin')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_users_role", "users", type_="check")
    op.drop_column("users", "role")
