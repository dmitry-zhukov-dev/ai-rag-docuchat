"""add_documents_file_path

Revision ID: 892e695eb5a3
Revises: a63d0c89b6ee
Create Date: 2026-10-19 06:35:21.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '892e695eb5a3'
down_revision: Union[str, Sequence[str], None] = 'a63d0c89b6ee'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'documents',
        sa.Column('file_path', sa.String(length=1024), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('documents', 'file_path')
