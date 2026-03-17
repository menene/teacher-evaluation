"""Reports — aggregated sentiment data for charts and tables."""
import json

from celery.result import AsyncResult
from fastapi import APIRouter, Depends
from sqlalchemy import func, case
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.evaluation import Evaluation, EvaluationComment, SentimentLabel, Topic
from app.worker.celery_app import celery_app

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/summary")
def get_summary(
    year: int = None,
    cycle: int = None,
    code_prefix: str = None,
    db: Session = Depends(get_db),
):
    """
    Returns sentiment comment counts grouped by year + cycle.
    Used to drive the line chart.
    """
    pos_id = db.query(SentimentLabel.id).filter(SentimentLabel.label == "positive").scalar()
    neu_id = db.query(SentimentLabel.id).filter(SentimentLabel.label == "neutral").scalar()
    neg_id = db.query(SentimentLabel.id).filter(SentimentLabel.label == "negative").scalar()

    q = (
        db.query(
            Evaluation.year,
            Evaluation.cycle,
            func.sum(case((EvaluationComment.sentiment_label_id == pos_id, 1), else_=0)).label("positive"),
            func.sum(case((EvaluationComment.sentiment_label_id == neu_id, 1), else_=0)).label("neutral"),
            func.sum(case((EvaluationComment.sentiment_label_id == neg_id, 1), else_=0)).label("negative"),
            func.count(EvaluationComment.id).label("total"),
        )
        .join(EvaluationComment, EvaluationComment.evaluation_id == Evaluation.id)
    )
    if year:        q = q.filter(Evaluation.year == year)
    if cycle:       q = q.filter(Evaluation.cycle == cycle)
    if code_prefix: q = q.filter(Evaluation.code_prefix == code_prefix)

    rows = q.group_by(Evaluation.year, Evaluation.cycle).order_by(Evaluation.year, Evaluation.cycle).all()

    return [
        {
            "year": r.year,
            "cycle": r.cycle,
            "label": f"{r.year} — Ciclo {r.cycle}",
            "positive": int(r.positive),
            "neutral": int(r.neutral),
            "negative": int(r.negative),
            "total": int(r.total),
        }
        for r in rows
    ]


@router.get("/summary/by-code")
def get_summary_by_code(
    year: int = None,
    cycle: int = None,
    code_prefix: str = None,
    db: Session = Depends(get_db),
):
    """Sentiment comment counts grouped by code_prefix."""
    pos_id = db.query(SentimentLabel.id).filter(SentimentLabel.label == "positive").scalar()
    neu_id = db.query(SentimentLabel.id).filter(SentimentLabel.label == "neutral").scalar()
    neg_id = db.query(SentimentLabel.id).filter(SentimentLabel.label == "negative").scalar()

    q = (
        db.query(
            Evaluation.code_prefix,
            func.sum(case((EvaluationComment.sentiment_label_id == pos_id, 1), else_=0)).label("positive"),
            func.sum(case((EvaluationComment.sentiment_label_id == neu_id, 1), else_=0)).label("neutral"),
            func.sum(case((EvaluationComment.sentiment_label_id == neg_id, 1), else_=0)).label("negative"),
        )
        .join(EvaluationComment, EvaluationComment.evaluation_id == Evaluation.id)
    )
    if year:        q = q.filter(Evaluation.year == year)
    if cycle:       q = q.filter(Evaluation.cycle == cycle)
    if code_prefix: q = q.filter(Evaluation.code_prefix == code_prefix)

    rows = q.group_by(Evaluation.code_prefix).order_by(Evaluation.code_prefix).all()
    return [{"label": r.code_prefix, "positive": int(r.positive), "neutral": int(r.neutral), "negative": int(r.negative)} for r in rows]


@router.get("/summary/by-cycle")
def get_summary_by_cycle(
    year: int = None,
    cycle: int = None,
    code_prefix: str = None,
    db: Session = Depends(get_db),
):
    """Sentiment comment counts grouped by cycle."""
    pos_id = db.query(SentimentLabel.id).filter(SentimentLabel.label == "positive").scalar()
    neu_id = db.query(SentimentLabel.id).filter(SentimentLabel.label == "neutral").scalar()
    neg_id = db.query(SentimentLabel.id).filter(SentimentLabel.label == "negative").scalar()

    q = (
        db.query(
            Evaluation.cycle,
            func.sum(case((EvaluationComment.sentiment_label_id == pos_id, 1), else_=0)).label("positive"),
            func.sum(case((EvaluationComment.sentiment_label_id == neu_id, 1), else_=0)).label("neutral"),
            func.sum(case((EvaluationComment.sentiment_label_id == neg_id, 1), else_=0)).label("negative"),
        )
        .join(EvaluationComment, EvaluationComment.evaluation_id == Evaluation.id)
    )
    if year:        q = q.filter(Evaluation.year == year)
    if cycle:       q = q.filter(Evaluation.cycle == cycle)
    if code_prefix: q = q.filter(Evaluation.code_prefix == code_prefix)

    rows = q.group_by(Evaluation.cycle).order_by(Evaluation.cycle).all()
    return [{"label": f"Ciclo {r.cycle}", "positive": int(r.positive), "neutral": int(r.neutral), "negative": int(r.negative)} for r in rows]


@router.get("/filters")
def get_filters(db: Session = Depends(get_db)):
    """Distinct values for the Año, Ciclo, and Código filter dropdowns."""
    years  = [r[0] for r in db.query(Evaluation.year).distinct().order_by(Evaluation.year.desc()).all()]
    cycles = [r[0] for r in db.query(Evaluation.cycle).distinct().order_by(Evaluation.cycle).all()]
    codes  = [r[0] for r in db.query(Evaluation.code_prefix).distinct().order_by(Evaluation.code_prefix).all()]
    return {"years": years, "cycles": cycles, "codes": codes}


@router.get("/evaluations")
def list_evaluations(
    page: int = 1,
    page_size: int = 25,
    year: int = None,
    cycle: int = None,
    code_prefix: str = None,
    db: Session = Depends(get_db),
):
    """Paginated evaluations with optional year/cycle/code_prefix filters."""
    base = (
        db.query(
            Evaluation,
            func.avg(EvaluationComment.sentiment_compound).label("avg_compound"),
            func.count(EvaluationComment.id).label("comment_count"),
        )
        .outerjoin(EvaluationComment, EvaluationComment.evaluation_id == Evaluation.id)
        .group_by(Evaluation.id)
        .order_by(Evaluation.year.desc(), Evaluation.cycle.desc(), Evaluation.number)
    )

    count_q = db.query(func.count(Evaluation.id))
    if year:
        base    = base.filter(Evaluation.year == year)
        count_q = count_q.filter(Evaluation.year == year)
    if cycle:
        base    = base.filter(Evaluation.cycle == cycle)
        count_q = count_q.filter(Evaluation.cycle == cycle)
    if code_prefix:
        base    = base.filter(Evaluation.code_prefix == code_prefix)
        count_q = count_q.filter(Evaluation.code_prefix == code_prefix)

    total = count_q.scalar()
    rows = base.offset((page - 1) * page_size).limit(page_size).all()

    def label(avg):
        if avg is None:
            return None
        if avg >= 0.05:
            return "positive"
        if avg <= -0.05:
            return "negative"
        return "neutral"

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": max(1, -(-total // page_size)),  # ceil division
        "items": [
            {
                "id": ev.id,
                "number": ev.number,
                "code_prefix": ev.code_prefix,
                "year": ev.year,
                "cycle": ev.cycle,
                "comment_count": count,
                "average_compound": round(float(avg), 4) if avg is not None else None,
                "overall_label": label(avg),
                "uploaded_at": ev.uploaded_at,
            }
            for ev, avg, count in rows
        ],
    }


@router.get("/evaluations/{evaluation_id}")
def get_evaluation_detail(evaluation_id: int, db: Session = Depends(get_db)):
    """Full comment detail for one evaluation."""
    ev = db.get(Evaluation, evaluation_id)
    if not ev:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Evaluation not found")

    label_map = {row.id: row.label for row in db.query(SentimentLabel).all()}

    comments = (
        db.query(EvaluationComment)
        .filter(EvaluationComment.evaluation_id == evaluation_id)
        .all()
    )

    scored = [c for c in comments if c.sentiment_compound is not None]
    avg = round(sum(c.sentiment_compound for c in scored) / len(scored), 4) if scored else None

    def lbl(avg):
        if avg is None: return None
        if avg >= 0.05: return "positive"
        if avg <= -0.05: return "negative"
        return "neutral"

    topic_map = {t.id: json.loads(t.keywords) for t in db.query(Topic).all()}

    return {
        "id": ev.id,
        "number": ev.number,
        "code_prefix": ev.code_prefix,
        "year": ev.year,
        "cycle": ev.cycle,
        "average_compound": avg,
        "overall_label": lbl(avg),
        "comments": [
            {
                "id": c.id,
                "comment": c.comment,
                "comment_en": c.comment_en,
                "comment_preprocessed": c.comment_preprocessed,
                "compound": c.sentiment_compound,
                "label": label_map.get(c.sentiment_label_id),
                "topic_id": c.topic_id,
                "topic_keywords": topic_map.get(c.topic_id),
            }
            for c in comments
        ],
    }


# ── Topic modeling ─────────────────────────────────────────────────────────────

@router.post("/run-topics")
def trigger_topic_modeling(n_topics: int = 5):
    """Queue on-demand global topic modeling. Returns a task_id to poll."""
    from app.worker.tasks import run_topic_modeling_task
    task = run_topic_modeling_task.delay(n_topics=n_topics)
    return {"task_id": task.id}


@router.get("/topics-status/{task_id}")
def get_topic_status(task_id: str):
    """Poll Celery result backend for topic modeling task progress."""
    result = AsyncResult(task_id, app=celery_app)
    return {
        "task_id": task_id,
        "status": result.status,   # PENDING | STARTED | SUCCESS | FAILURE
        "ready": result.ready(),
        "result": result.result if result.ready() and not result.failed() else None,
        "error": str(result.result) if result.failed() else None,
    }


@router.get("/topics")
def get_topics(db: Session = Depends(get_db)):
    """Return all topics with keyword list, comment count, and sentiment distribution."""
    pos_id = db.query(SentimentLabel.id).filter(SentimentLabel.label == "positive").scalar()
    neu_id = db.query(SentimentLabel.id).filter(SentimentLabel.label == "neutral").scalar()
    neg_id = db.query(SentimentLabel.id).filter(SentimentLabel.label == "negative").scalar()

    topics = db.query(Topic).order_by(Topic.id).all()
    result = []
    for t in topics:
        rows = (
            db.query(
                func.count(EvaluationComment.id).label("total"),
                func.sum(case((EvaluationComment.sentiment_label_id == pos_id, 1), else_=0)).label("positive"),
                func.sum(case((EvaluationComment.sentiment_label_id == neu_id, 1), else_=0)).label("neutral"),
                func.sum(case((EvaluationComment.sentiment_label_id == neg_id, 1), else_=0)).label("negative"),
            )
            .filter(EvaluationComment.topic_id == t.id)
            .one()
        )
        result.append({
            "id": t.id,
            "keywords": json.loads(t.keywords),
            "weight": t.weight,
            "comment_count": int(rows.total),
            "sentiment": {
                "positive": int(rows.positive),
                "neutral":  int(rows.neutral),
                "negative": int(rows.negative),
            },
            "created_at": t.created_at,
        })
    return result
