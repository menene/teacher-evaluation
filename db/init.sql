-- Teacher Evaluation Analysis — Initial Schema
-- This file is executed once when the MariaDB container is first created.

CREATE TABLE IF NOT EXISTS sentiment_labels (
    id    TINYINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    label VARCHAR(20) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO sentiment_labels (label) VALUES ('positive'), ('neutral'), ('negative');


CREATE TABLE IF NOT EXISTS evaluations (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    job_id       CHAR(36)        NULL COMMENT 'Source job UUID',
    number       INT             NOT NULL COMMENT 'Evaluation number',
    code_prefix  CHAR(2)         NOT NULL COMMENT 'Two-letter anonymisation code',
    total        TINYINT UNSIGNED NOT NULL COMMENT 'Score 0–100',
    cycle        INT             NOT NULL COMMENT 'Academic cycle number',
    year         YEAR            NOT NULL,
    uploaded_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_eval_year  (year),
    INDEX idx_eval_cycle (cycle),
    INDEX idx_eval_job   (job_id),
    CONSTRAINT chk_total CHECK (total BETWEEN 0 AND 100)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE IF NOT EXISTS topics (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    keywords   TEXT    NOT NULL COMMENT 'JSON array of top keywords',
    weight     FLOAT   NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE IF NOT EXISTS evaluation_comments (
    id                INT AUTO_INCREMENT PRIMARY KEY,
    evaluation_id     INT          NOT NULL,
    sentiment_label_id TINYINT UNSIGNED NULL,
    topic_id           INT              NULL,
    comment               TEXT             NOT NULL,
    comment_en            TEXT             NULL,
    comment_preprocessed  TEXT             NULL,
    sentiment_compound    FLOAT            NULL,
    CONSTRAINT fk_comment_eval
        FOREIGN KEY (evaluation_id) REFERENCES evaluations(id) ON DELETE CASCADE,
    CONSTRAINT fk_comment_sentiment
        FOREIGN KEY (sentiment_label_id) REFERENCES sentiment_labels(id) ON DELETE SET NULL,
    CONSTRAINT fk_comment_topic
        FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE SET NULL,
    INDEX idx_comment_eval      (evaluation_id),
    INDEX idx_comment_sentiment (sentiment_label_id),
    INDEX idx_comment_topic     (topic_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS jobs (
    id           CHAR(36)     PRIMARY KEY COMMENT 'UUID',
    evaluation_id INT          NULL,
    filename     VARCHAR(255) NOT NULL,
    status       VARCHAR(20)  NOT NULL DEFAULT 'pending'
                 COMMENT 'pending|parsing|translating|sentiment|topics|complete|skipped|failed',
    error        TEXT         NULL,
    notes        TEXT         NULL COMMENT 'JSON list of warnings',
    created_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_job_eval
        FOREIGN KEY (evaluation_id) REFERENCES evaluations(id) ON DELETE SET NULL,
    INDEX idx_job_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
