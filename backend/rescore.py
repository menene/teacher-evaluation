import argparse

from app.db.session import SessionLocal
from app.models.evaluation import EvaluationComment, SentimentLabel
from app.services.sentiment import preprocessing, _score

parser = argparse.ArgumentParser()
parser.add_argument("--force", action="store_true", help="Re-score already scored comments")
args = parser.parse_args()

db = SessionLocal()

label_map = {row.label: row.id for row in db.query(SentimentLabel).all()}

query = db.query(EvaluationComment).filter(EvaluationComment.comment_en.isnot(None))
if not args.force:
    query = query.filter(EvaluationComment.sentiment_compound.is_(None))

comments = query.all()

if not comments:
    print("Nothing to score.")
    db.close()
else:
    print(f"Scoring {len(comments)} comment(s){'  (forced)' if args.force else ''}...")
    for i, comment in enumerate(comments, 1):
        comment.comment_preprocessed = preprocessing(comment.comment_en)
        result = _score(comment.comment_en)
        comment.sentiment_compound = result["compound"]
        comment.sentiment_label_id = label_map.get(result["label"])

        if i % 500 == 0:
            db.commit()
            print(f"  [{i}/{len(comments)}] committed...")

    db.commit()
    db.close()
    print("All re-scored.")
