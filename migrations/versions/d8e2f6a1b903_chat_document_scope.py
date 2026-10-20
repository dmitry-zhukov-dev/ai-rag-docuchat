"""Add chat-scoped content identity; preserve legacy rows untouched.

Source only: applying this migration requires separate authorization.
"""
from alembic import op
import sqlalchemy as sa

revision = "d8e2f6a1b903"
down_revision = "c4f1a2b3d4e5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("conversation_id", sa.Integer(), nullable=True))
    op.add_column("documents", sa.Column("file_hash", sa.String(64), nullable=True))
    op.create_unique_constraint("uq_conversations_id_workspace", "conversations", ["id", "workspace_id"])
    op.create_foreign_key(
        "fk_documents_conversation_workspace", "documents", "conversations",
        ["conversation_id", "workspace_id"], ["id", "workspace_id"],
    )
    # PostgreSQL's default NULLS DISTINCT permits all unchanged legacy rows.
    # MATCH SIMPLE skips the composite FK when conversation_id is NULL.
    op.create_unique_constraint("uq_documents_conversation_hash", "documents", ["conversation_id", "file_hash"])
    op.create_check_constraint(
        "ck_documents_scope_hash", "documents",
        "(conversation_id IS NULL AND file_hash IS NULL) OR "
        "(conversation_id IS NOT NULL AND file_hash IS NOT NULL AND length(file_hash) = 64)",
    )


def downgrade() -> None:
    # Removing scope would expose new private documents to other workspace chats.
    raise RuntimeError("Automatic downgrade is unsafe after scoped uploads; requires a reviewed data plan.")
