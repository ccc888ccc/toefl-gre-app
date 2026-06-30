"""Lightweight, idempotent schema migrations for the SQLite database.

This app is single-file (no Alembic), so on startup we bring an EXISTING database
up to the current model:

  * users.role                  -- role-based access (admin vs member)
  * review_events.user_id       -- per-user streak / daily counts
  * vocab_reviews rebuilt        -- SRS progress keyed by (user_id, card_id)
                                   instead of a single global row per card

On a fresh database create_all() already builds the current schema, so this is a
no-op. The functions only ever ADD columns or rebuild vocab_reviews, backfilling
existing progress to the admin account, and they make a one-time file backup
before any structural change.
"""
import os
import shutil

from sqlalchemy import text
from sqlalchemy.engine import Engine


def _columns(conn, table: str) -> set[str]:
    return {row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))}


def _table_exists(conn, table: str) -> bool:
    return conn.execute(
        text("SELECT name FROM sqlite_master WHERE type='table' AND name=:n"),
        {"n": table},
    ).first() is not None


def run_migrations(engine: Engine, admin_username: str) -> None:
    db_path = engine.url.database  # local file path for sqlite

    with engine.begin() as conn:
        if not _table_exists(conn, "users"):
            return  # brand-new DB: create_all already built the current schema

        needs_role = "role" not in _columns(conn, "users")
        needs_event_uid = (_table_exists(conn, "review_events")
                           and "user_id" not in _columns(conn, "review_events"))
        needs_review_rebuild = (_table_exists(conn, "vocab_reviews")
                                and "user_id" not in _columns(conn, "vocab_reviews"))

        if not (needs_role or needs_event_uid or needs_review_rebuild):
            return  # already migrated

        # One-time safety backup before touching structure.
        if db_path and os.path.exists(db_path):
            bak = db_path + ".premigration.bak"
            if not os.path.exists(bak):
                shutil.copy(db_path, bak)

        # 1) users.role + promote the .env account to admin.
        if needs_role:
            conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(16) DEFAULT 'member'"))
        conn.execute(text("UPDATE users SET role='admin' WHERE username=:u"),
                     {"u": admin_username})

        # Admin id used to backfill existing (single-user) progress.
        row = conn.execute(text("SELECT id FROM users WHERE username=:u"),
                           {"u": admin_username}).first()
        admin_id = row[0] if row else conn.execute(text("SELECT MIN(id) FROM users")).scalar()

        # 2) review_events.user_id
        if needs_event_uid:
            conn.execute(text("ALTER TABLE review_events ADD COLUMN user_id INTEGER"))
            conn.execute(text("UPDATE review_events SET user_id=:a WHERE user_id IS NULL"),
                         {"a": admin_id})

        # 3) Rebuild vocab_reviews keyed by (user_id, card_id). Nothing references
        #    vocab_reviews by FK, so a drop+rename is safe.
        if needs_review_rebuild:
            conn.execute(text("""
                CREATE TABLE vocab_reviews_new (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id),
                    card_id INTEGER REFERENCES vocab_cards(id),
                    ease_factor FLOAT,
                    interval_days INTEGER,
                    repetitions INTEGER,
                    due_date DATE,
                    last_reviewed DATETIME,
                    total_seen INTEGER,
                    total_correct INTEGER
                )
            """))
            conn.execute(text("""
                INSERT INTO vocab_reviews_new
                    (id, user_id, card_id, ease_factor, interval_days, repetitions,
                     due_date, last_reviewed, total_seen, total_correct)
                SELECT id, :a, card_id, ease_factor, interval_days, repetitions,
                       due_date, last_reviewed, total_seen, total_correct
                FROM vocab_reviews
            """), {"a": admin_id})
            conn.execute(text("DROP TABLE vocab_reviews"))
            conn.execute(text("ALTER TABLE vocab_reviews_new RENAME TO vocab_reviews"))
            conn.execute(text(
                "CREATE UNIQUE INDEX uq_vocab_reviews_user_card "
                "ON vocab_reviews(user_id, card_id)"))
            conn.execute(text(
                "CREATE INDEX ix_vocab_reviews_user_id ON vocab_reviews(user_id)"))
            conn.execute(text(
                "CREATE INDEX ix_vocab_reviews_card_id ON vocab_reviews(card_id)"))
            conn.execute(text(
                "CREATE INDEX ix_vocab_reviews_due_date ON vocab_reviews(due_date)"))
