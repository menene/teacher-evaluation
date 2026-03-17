from app.db.session import SessionLocal
from app.models.evaluation import Evaluation
from app.services.sentiment import run_sentiment

db = SessionLocal()
ids = [e.id for e in db.query(Evaluation.id).all()]
db.close()

for eid in ids:
    run_sentiment(eid)
    print(f"Done evaluation {eid}")

print("All re-scored.")
