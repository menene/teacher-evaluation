"""
Sentiment analysis pipeline.
Step 1 — preprocess English comments (tokenise, remove stop words, lemmatise).
Step 2 — score with VADER and persist label + compound score.
"""
import logging

import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from textblob import TextBlob
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from app.db.session import SessionLocal
from app.models.evaluation import EvaluationComment, SentimentLabel

logger = logging.getLogger(__name__)

_analyzer = SentimentIntensityAnalyzer()

# ── Domain lexicon patch ───────────────────────────────────────────────────────
# VADER is trained on social media; these words are neutral or positive in
# educational feedback but score negatively in the default lexicon.
_analyzer.lexicon.update({
    # Student questions/uncertainties → neutral in this context
    "doubt": 0.0,
    "doubts": 0.0,
    "question": 0.0,
    "questions": 0.0,
    "uncertain": 0.0,
    "uncertainty": 0.0,
    # "no hassle" / "no problems" — negation handles the flip but base score is too extreme
    "hassle": -0.5,
    "inconvenience": -0.5,
    "inconveniences": -0.5,
    "problem": -0.5,
    "problems": -0.5,
    "issue": -0.5,
    "issues": -0.5,
    # Answering questions is a positive teaching behavior
    "answer": 0.5,
    "answers": 0.5,
    "respond": 0.5,
    "responds": 0.5,
    # Teaching quality words underweighted by VADER
    "understandable": 2.5,
    "mastery": 2.5,
    "knowledgeable": 2.5,
    "available": 1.5,
    "accessible": 1.5,
    "dedicated": 2.0,
    "passionate": 2.0,
    "patient": 2.0,
    "organized": 1.5,
    "dynamic": 1.5,
})

_lemmatizer = WordNetLemmatizer()
_stop_words = set(stopwords.words("english"))


# ── Text preprocessing ────────────────────────────────────────────────────────

def preprocessing(text: str) -> str:
    tokens = [
        word
        for sent in nltk.sent_tokenize(text)
        for word in nltk.word_tokenize(sent)
    ]
    tokens = [t for t in tokens if t not in _stop_words]
    tokens = [t for t in tokens if len(t) >= 3]
    tokens = [t.lower() for t in tokens]
    tokens = [_lemmatizer.lemmatize(t) for t in tokens]
    return " ".join(tokens)


# ── Ensemble scoring (VADER + TextBlob) ──────────────────────────────────────
# VADER: strong on slang/punctuation/caps, weak on negation of extreme words.
# TextBlob: pattern-based, handles "no hassle" / "not bad" negation correctly.
# We average both compound scores for a more robust result.

def _textblob_compound(text: str) -> float:
    """Convert TextBlob polarity [-1, 1] to a compound score."""
    return TextBlob(text).sentiment.polarity


def _score(text: str) -> dict:
    vader_compound = _analyzer.polarity_scores(text)["compound"]
    tb_compound = _textblob_compound(text)
    # Weighted average: equal weight — adjust if one proves more reliable
    compound = round((vader_compound + tb_compound) / 2, 4)
    if compound >= 0.05:
        label = "positive"
    elif compound <= -0.05:
        label = "negative"
    else:
        label = "neutral"
    return {"compound": compound, "label": label}


# ── Pipeline step ─────────────────────────────────────────────────────────────

def run_sentiment(evaluation_id: int) -> None:
    """
    Preprocess and score all translated comments for an evaluation.
    Writes comment_preprocessed, sentiment_compound, and sentiment_label_id
    back to each EvaluationComment row.
    """
    db = SessionLocal()
    try:
        # Build label → id lookup
        label_map = {
            row.label: row.id
            for row in db.query(SentimentLabel).all()
        }

        comments = (
            db.query(EvaluationComment)
            .filter(
                EvaluationComment.evaluation_id == evaluation_id,
                EvaluationComment.comment_en.isnot(None),
            )
            .all()
        )

        for comment in comments:
            # Preprocess for topic modeling (bag of lemmas)
            comment.comment_preprocessed = preprocessing(comment.comment_en)
            # Score on natural English text — VADER needs context, intensifiers, punctuation
            result = _score(comment.comment_en)
            comment.sentiment_compound = result["compound"]
            comment.sentiment_label_id = label_map.get(result["label"])

        db.commit()
        logger.info(
            "Sentiment done for evaluation %d — %d comment(s) scored",
            evaluation_id, len(comments),
        )
    except Exception:
        db.rollback()
        logger.exception("Sentiment analysis failed for evaluation %d", evaluation_id)
        raise
    finally:
        db.close()
