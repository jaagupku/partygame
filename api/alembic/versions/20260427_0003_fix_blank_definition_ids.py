"""fix invalid definition ids

Revision ID: 20260427_0003
Revises: 20260424_0002
Create Date: 2026-04-27

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260427_0003"
down_revision: str | None = "20260424_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(sa.text("""
            DO $$
            DECLARE
                invalid_definition record;
                base_id text;
                candidate_id text;
                hash_input text;
                suffix integer;
            BEGIN
                FOR invalid_definition IN
                    SELECT id, title, owner_user_id, created_at
                    FROM game_definitions
                    WHERE id !~ '^[a-z0-9][a-z0-9_-]{0,79}$'
                LOOP
                    base_id := COALESCE(
                        NULLIF(
                            substring(
                                btrim(
                                    regexp_replace(
                                        lower(trim(coalesce(nullif(invalid_definition.title, ''), 'definition'))),
                                        '[^a-z0-9]+',
                                        '_',
                                        'g'
                                    ),
                                    '_'
                                )
                                from 1 for 48
                            ),
                            ''
                        ),
                        'definition'
                    );
                    hash_input := coalesce(invalid_definition.id, '')
                        || coalesce(invalid_definition.title, '')
                        || coalesce(invalid_definition.owner_user_id, '')
                        || coalesce(invalid_definition.created_at::text, '');
                    candidate_id := base_id
                        || '_fixed_'
                        || substring(
                            md5(hash_input)
                            from 1 for 8
                        );
                    suffix := 2;

                    WHILE EXISTS (
                        SELECT 1 FROM game_definitions WHERE id = candidate_id
                    ) LOOP
                        candidate_id := base_id
                            || '_fixed_'
                            || substring(
                                md5(hash_input)
                                from 1 for 8
                            )
                            || '_'
                            || suffix::text;
                        suffix := suffix + 1;
                    END LOOP;

                    UPDATE game_definitions
                    SET
                        id = candidate_id,
                        payload = jsonb_set(payload, '{id}', to_jsonb(candidate_id), true),
                        updated_at = now()
                    WHERE id = invalid_definition.id;
                END LOOP;
            END $$;
            """))
    op.execute(sa.text("""
            UPDATE game_definitions
            SET
                payload = jsonb_set(payload, '{id}', to_jsonb(id), true),
                updated_at = now()
            WHERE payload->>'id' IS DISTINCT FROM id
            """))
    op.create_check_constraint(
        "ck_game_definitions_id_format",
        "game_definitions",
        "id ~ '^[a-z0-9][a-z0-9_-]{0,79}$'",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_game_definitions_id_format",
        "game_definitions",
        type_="check",
    )
