"""
Translate all untranslated comments (comment_en IS NULL) across all evaluations.

Usage:
    python translate.py
"""
from app.db.session import SessionLocal
from app.models.evaluation import EvaluationComment
from app.services.translation import translate_evaluation_comments

db = SessionLocal()
ids = [
    row.evaluation_id
    for row in (
        db.query(EvaluationComment.evaluation_id)
        .filter(EvaluationComment.comment_en.is_(None))
        .distinct()
        .all()
    )
]
db.close()

if not ids:
    print("Nothing to translate.")
else:
    print(f"Found {len(ids)} evaluation(s) with untranslated comments.")
    for i, eid in enumerate(ids, 1):
        translate_evaluation_comments(eid)
        print(f"[{i}/{len(ids)}] Translated evaluation {eid}")
    print("All translated.")
