"""
Migration: add topics table and topic_id column to evaluation_comments.
Run once on existing databases:
    docker compose exec backend python migrate_topics.py
"""
from sqlalchemy import text
from app.db.session import engine

with engine.connect() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS topics (
            id         INT AUTO_INCREMENT PRIMARY KEY,
            keywords   TEXT    NOT NULL COMMENT 'JSON array of top keywords',
            weight     FLOAT   NOT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """))

    conn.execute(text("""
        ALTER TABLE evaluation_comments
        ADD COLUMN IF NOT EXISTS topic_id INT NULL
    """))

    # Add FK only if it doesn't exist yet
    fk_exists = conn.execute(text("""
        SELECT COUNT(*) FROM information_schema.TABLE_CONSTRAINTS
        WHERE CONSTRAINT_SCHEMA = DATABASE()
          AND TABLE_NAME = 'evaluation_comments'
          AND CONSTRAINT_NAME = 'fk_comment_topic'
    """)).scalar()

    if not fk_exists:
        conn.execute(text("""
            ALTER TABLE evaluation_comments
            ADD CONSTRAINT fk_comment_topic
                FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE SET NULL
        """))

    conn.commit()

print("Migration complete.")
