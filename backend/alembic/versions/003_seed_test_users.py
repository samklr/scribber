"""Seed test users

Revision ID: 003_seed_users
Revises: 002_seed_models
Create Date: 2024-01-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "003_seed_users"
down_revision: Union[str, None] = "002_seed_models"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Pre-computed bcrypt hashes for test credentials
# Admin: admin@example.com / admin123
# User: user@example.com / user123
ADMIN_PASSWORD_HASH = "$2b$12$F8LENqfeRLUtezOqC7zZJuClbQX1Yx62vxqiolGG6ZddwAzfzqYQa"
USER_PASSWORD_HASH = "$2b$12$qHU5VEA92PxwR9Z8Kq2AxuV0KpF3F7D3nFMApmUvSY6THQJI.ETaK"


def upgrade() -> None:
    # Create test users with pre-computed password hashes
    users_table = sa.table(
        "users",
        sa.column("id", sa.Integer),
        sa.column("email", sa.String),
        sa.column("name", sa.String),
        sa.column("hashed_password", sa.String),
        sa.column("is_admin", sa.Boolean),
        sa.column("is_active", sa.Boolean),
    )

    op.bulk_insert(
        users_table,
        [
            {
                "id": 1,
                "email": "admin@example.com",
                "name": "Admin User",
                "hashed_password": ADMIN_PASSWORD_HASH,
                "is_admin": True,
                "is_active": True,
            },
            {
                "id": 2,
                "email": "user@example.com",
                "name": "Test User",
                "hashed_password": USER_PASSWORD_HASH,
                "is_admin": False,
                "is_active": True,
            },
        ],
    )


def downgrade() -> None:
    op.execute("DELETE FROM users WHERE email IN ('admin@example.com', 'user@example.com')")
