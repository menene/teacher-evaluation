"""Job status endpoint."""
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.evaluation import Evaluation, EvaluationComment, SentimentLabel
from app.models.job import Job

router = APIRouter(prefix="/jobs", tags=["jobs"])

STEP_ORDER = ["pending", "parsing", "translating", "sentiment", "topics", "complete"]


def _label_from_compound(avg: float) -> str:
    if avg >= 0.05:
        return "positive"
    elif avg <= -0.05:
        return "negative"
    return "neutral"


def _serialize_evaluation(ev: Evaluation, comments: list[EvaluationComment],
                           label_map: dict) -> dict:
    scored = [c for c in comments if c.sentiment_compound is not None]
    avg_compound = round(sum(c.sentiment_compound for c in scored) / len(scored), 4) if scored else None

    return {
        "id": ev.id,
        "number": ev.number,
        "code_prefix": ev.code_prefix,
        "year": ev.year,
        "cycle": ev.cycle,
        "average_compound": avg_compound,
        "overall_label": _label_from_compound(avg_compound) if avg_compound is not None else None,
        "comments": [
            {
                "id": c.id,
                "text": c.comment,
                "text_en": c.comment_en,
                "compound": c.sentiment_compound,
                "label": label_map.get(c.sentiment_label_id),
            }
            for c in comments
        ],
    }


@router.get("/{job_id}")
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    current = job.status
    step_index = STEP_ORDER.index(current) if current in STEP_ORDER else -1

    evaluations = None
    if current in ("complete", "skipped"):
        label_map = {row.id: row.label for row in db.query(SentimentLabel).all()}

        rows = db.query(Evaluation).filter(Evaluation.job_id == job_id).all()
        if not rows and job.evaluation_id:
            ev = db.get(Evaluation, job.evaluation_id)
            rows = [ev] if ev else []

        if rows:
            evaluations = []
            for ev in rows:
                comments = (
                    db.query(EvaluationComment)
                    .filter(EvaluationComment.evaluation_id == ev.id)
                    .all()
                )
                evaluations.append(_serialize_evaluation(ev, comments, label_map))

    return {
        "id": job.id,
        "filename": job.filename,
        "status": current,
        "step_index": step_index,
        "total_steps": len(STEP_ORDER),
        "evaluation_id": job.evaluation_id,
        "evaluations": evaluations,
        "warnings": json.loads(job.notes) if job.notes else [],
        "error": job.error,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
    }
