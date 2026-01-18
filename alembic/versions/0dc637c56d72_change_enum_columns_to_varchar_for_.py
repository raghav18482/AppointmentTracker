"""Change enum columns to VARCHAR for native_enum=False

Revision ID: 0dc637c56d72
Revises: 609b4a493af9
Create Date: 2025-12-14 18:51:51.935729

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0dc637c56d72'
down_revision: Union[str, None] = '609b4a493af9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Change enum columns to VARCHAR to support native_enum=False
    # This allows storing lowercase enum values instead of enum member names
    op.execute("ALTER TABLE businesses ALTER COLUMN type TYPE VARCHAR USING type::text")
    op.execute("ALTER TABLE user_businesses ALTER COLUMN role TYPE VARCHAR USING role::text")
    
    # Drop the enum types (optional, but cleans up)
    op.execute("DROP TYPE IF EXISTS businesstype")
    op.execute("DROP TYPE IF EXISTS userrole")


def downgrade() -> None:
    # Recreate enum types (only if they don't exist)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE businesstype AS ENUM ('CLINIC', 'HOSPITAL', 'SALON', 'SPA', 'FITNESS', 'OTHER');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE userrole AS ENUM ('OWNER', 'STAFF');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Convert back to enum (this might fail if data doesn't match)
    op.execute("ALTER TABLE businesses ALTER COLUMN type TYPE businesstype USING type::businesstype")
    op.execute("ALTER TABLE user_businesses ALTER COLUMN role TYPE userrole USING role::userrole")

