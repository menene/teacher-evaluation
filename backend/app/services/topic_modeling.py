"""
Global topic modeling using NMF + TF-IDF.
Runs across ALL preprocessed comments in the database, clears previous results,
and assigns each comment to its dominant topic.
"""
import json
import logging

import numpy as np
from sklearn.decomposition import NMF
from sklearn.feature_extraction.text import TfidfVectorizer

from app.db.session import SessionLocal
from app.models.evaluation import EvaluationComment, Topic

logger = logging.getLogger(__name__)


def run_topic_modeling(n_topics: int = 5, n_top_words: int = 8) -> list[dict]:
    """
    Fit a global NMF topic model on all preprocessed comments, persist
    topics and per-comment assignments to the database, replacing any
    previously computed topics.

    Returns the list of topic dicts that were saved.
    """
    db = SessionLocal()
    try:
        # ── Fetch all preprocessed comments ──────────────────────────────────
        comments = (
            db.query(EvaluationComment)
            .filter(EvaluationComment.comment_preprocessed.isnot(None))
            .all()
        )

        texts = [c.comment_preprocessed for c in comments]
        valid = [(c, t) for c, t in zip(comments, texts) if t and t.strip()]

        if not valid:
            logger.warning("No preprocessed comments found — skipping topic modeling")
            return []

        comments_valid, texts_valid = zip(*valid)

        # ── TF-IDF vectorisation ──────────────────────────────────────────────
        vectorizer = TfidfVectorizer(
            max_df=0.95,
            min_df=1,
            stop_words="english",
            max_features=1000,
        )
        tfidf = vectorizer.fit_transform(texts_valid)

        actual_n_topics = min(n_topics, tfidf.shape[0])

        # ── NMF topic model ───────────────────────────────────────────────────
        model = NMF(n_components=actual_n_topics, random_state=42, max_iter=400)
        W = model.fit_transform(tfidf)   # document-topic matrix (n_docs × n_topics)

        feature_names = vectorizer.get_feature_names_out()

        # ── Clear previous topics (FK ON DELETE SET NULL resets comment.topic_id) ──
        db.query(Topic).delete()
        db.flush()

        # ── Insert new topics ─────────────────────────────────────────────────
        topic_objs = []
        for idx, component in enumerate(model.components_):
            top_indices = component.argsort()[: -(n_top_words + 1) : -1]
            keywords = [feature_names[i] for i in top_indices]
            topic = Topic(
                keywords=json.dumps(keywords),
                weight=float(component.max()),
            )
            db.add(topic)
            topic_objs.append(topic)

        db.flush()  # get topic PKs

        # ── Assign each comment to its dominant topic ─────────────────────────
        dominant = np.argmax(W, axis=1)
        for comment, topic_idx in zip(comments_valid, dominant):
            comment.topic_id = topic_objs[topic_idx].id

        db.commit()

        result = [
            {
                "id": t.id,
                "keywords": json.loads(t.keywords),
                "weight": t.weight,
            }
            for t in topic_objs
        ]
        logger.info(
            "Topic modeling complete — %d topic(s) from %d comment(s)",
            len(result), len(comments_valid),
        )
        return result

    except Exception:
        db.rollback()
        logger.exception("Topic modeling failed")
        raise
    finally:
        db.close()
