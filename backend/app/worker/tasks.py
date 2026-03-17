"""Celery tasks — full PDF processing pipeline + on-demand topic modeling."""
import json
import logging
import os

from app.db.session import SessionLocal
from app.models.evaluation import Evaluation, EvaluationComment
from app.models.job import Job
from app.services.pdf_parser import parse_pdf
from app.services.sentiment import run_sentiment
from app.services.translation import translate_evaluation_comments
from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)


def _set_status(db, job_id: str, status: str, **kwargs):
    job = db.get(Job, job_id)
    if job:
        job.status = status
        for k, v in kwargs.items():
            setattr(job, k, v)
        db.commit()


@celery_app.task(bind=True, max_retries=3)
def process_pdf(self, job_id: str, file_path: str):
    """Full pipeline: parse all evaluations → save → translate → sentiment → topics."""
    db = SessionLocal()
    try:
        # ── Step 1: Parse all evaluations in the PDF ──────────────────────────
        _set_status(db, job_id, "parsing")
        parsed = parse_pdf(file_path)
        logger.info("Job %s: found %d evaluation(s) in PDF", job_id, len(parsed))

        saved_ids = []
        skipped = 0
        warnings = []

        for item in parsed:
            fields = item["fields"]
            comments_text = item["comments"]
            number = fields.get("number")

            # Skip evaluations with no comments
            if not comments_text:
                msg = f"Evaluación No. {number or '?'}: no tiene comentarios y no será guardada."
                warnings.append(msg)
                logger.info("Job %s: %s", job_id, msg)
                continue

            # Skip duplicates
            if number and db.query(Evaluation).filter(Evaluation.number == number).first():
                skipped += 1
                logger.info("Job %s: evaluation %s already exists, skipping", job_id, number)
                continue

            evaluation = Evaluation(
                job_id=job_id,
                number=number or 0,
                code_prefix=fields.get("code_prefix", "??"),
                year=fields.get("year", 0),
                cycle=fields.get("cycle", 0),
                total=0,
            )
            db.add(evaluation)
            db.flush()

            for text in comments_text:
                db.add(EvaluationComment(evaluation_id=evaluation.id, comment=text))

            db.commit()
            saved_ids.append(evaluation.id)

        notes_json = json.dumps(warnings) if warnings else None

        if not saved_ids and skipped == len(parsed):
            # All were duplicates
            first_existing = db.query(Evaluation).filter(
                Evaluation.number == (parsed[0]["fields"].get("number") or 0)
            ).first()
            _set_status(db, job_id, "skipped",
                        evaluation_id=first_existing.id if first_existing else None,
                        notes=notes_json)
            return

        if not saved_ids:
            # All evaluations had no comments (or all skipped for other reasons)
            _set_status(db, job_id, "complete", notes=notes_json)
            return

        # Use first saved evaluation as the job's primary reference
        _set_status(db, job_id, "translating",
                    evaluation_id=saved_ids[0],
                    notes=notes_json)

        # ── Step 2: Translate ─────────────────────────────────────────────────
        for eval_id in saved_ids:
            translate_evaluation_comments(eval_id)
        _set_status(db, job_id, "sentiment")

        # ── Step 3: Sentiment ─────────────────────────────────────────────────
        for eval_id in saved_ids:
            run_sentiment(eval_id)
        _set_status(db, job_id, "topics")

        # ── Step 4: Topic modeling (placeholder — run on-demand via /run-topics) ──
        _set_status(db, job_id, "complete")
        logger.info("Job %s: complete — saved %d, skipped %d", job_id, len(saved_ids), skipped)

    except Exception as exc:
        db.rollback()
        try:
            _set_status(db, job_id, "failed", error=str(exc))
        except Exception:
            pass
        logger.exception("Pipeline failed for job %s", job_id)
        raise self.retry(exc=exc, countdown=5)
    finally:
        db.close()
        if os.path.exists(file_path):
            os.unlink(file_path)


@celery_app.task(bind=True)
def run_topic_modeling_task(self, n_topics: int = 5):
    """On-demand global topic modeling across all preprocessed comments."""
    from app.services.topic_modeling import run_topic_modeling
    topics = run_topic_modeling(n_topics=n_topics)
    return {"status": "complete", "n_topics": len(topics)}
