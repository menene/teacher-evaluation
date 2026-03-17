"""Translation service — DeepL (primary) with LibreTranslate (self-hosted fallback)."""
import logging

import requests

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.evaluation import EvaluationComment

logger = logging.getLogger(__name__)


def _translate_deepl(texts: list[str]) -> list[str]:
    import deepl
    translator = deepl.Translator(settings.DEEPL_API_KEY)
    results = translator.translate_text(texts, source_lang="ES", target_lang="EN-US")
    return [r.text for r in results]


def _translate_libretranslate(texts: list[str]) -> list[str]:
    """Translate a batch via LibreTranslate one text at a time."""
    url = f"{settings.LIBRETRANSLATE_URL}/translate"
    translated = []
    for text in texts:
        resp = requests.post(url, json={"q": text, "source": "es", "target": "en"}, timeout=30)
        resp.raise_for_status()
        translated.append(resp.json()["translatedText"])
    return translated


def translate_evaluation_comments(evaluation_id: int) -> None:
    """Translate all untranslated comments for an evaluation.

    Uses DeepL if DEEPL_API_KEY is set, otherwise falls back to LibreTranslate.
    """
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

        if settings.DEEPL_API_KEY:
            try:
                logger.info("Translating %d comments via DeepL (evaluation %d)", len(texts), evaluation_id)
                translated = _translate_deepl(texts)
            except Exception as e:
                logger.warning("DeepL failed (%s), falling back to LibreTranslate", e)
                translated = _translate_libretranslate(texts)
        else:
            logger.info("Translating %d comments via LibreTranslate (evaluation %d)", len(texts), evaluation_id)
            translated = _translate_libretranslate(texts)

        for comment, text in zip(comments, translated):
            comment.comment_en = text

        db.commit()
        logger.info("Translated %d comments for evaluation %d", len(comments), evaluation_id)
    except Exception:
        db.rollback()
        logger.exception("Translation failed for evaluation %d", evaluation_id)
    finally:
        db.close()
