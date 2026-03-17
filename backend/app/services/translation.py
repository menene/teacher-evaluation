"""DeepL translation service."""
import logging

import deepl

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.evaluation import EvaluationComment

logger = logging.getLogger(__name__)


def translate_evaluation_comments(evaluation_id: int) -> None:
    """Background task: translate all untranslated comments for an evaluation."""
    if not settings.DEEPL_API_KEY:
        logger.warning("DEEPL_API_KEY not set — skipping translation")
        return

    translator = deepl.Translator(settings.DEEPL_API_KEY)
    db = SessionLocal()
    try:
        comments = (
            db.query(EvaluationComment)
            .filter(
                EvaluationComment.evaluation_id == evaluation_id,
                EvaluationComment.comment_en.is_(None),
            )
            .all()
        )

        if not comments:
            return

        texts = [c.comment for c in comments]
        results = translator.translate_text(texts, source_lang="ES", target_lang="EN-US")

        for comment, result in zip(comments, results):
            comment.comment_en = result.text

        db.commit()
        logger.info("Translated %d comments for evaluation %d", len(comments), evaluation_id)
    except Exception:
        db.rollback()
        logger.exception("Translation failed for evaluation %d", evaluation_id)
    finally:
        db.close()
