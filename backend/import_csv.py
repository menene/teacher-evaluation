"""
Import teacher evaluation comments from a CSV file into the database.

CSV format expected:
    comments_texts,idProfesor,idMateria,ciclo,anio

Each unique (idProfesor, idMateria, ciclo, anio) combination becomes one
Evaluation record. All comments for that group are inserted as
EvaluationComment rows, then translated (ES→EN via DeepL) and scored.

Usage:
    python import_csv.py data/your_file.csv
    python import_csv.py data/your_file.csv --no-sentiment
    python import_csv.py data/your_file.csv --no-translate
"""
import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

from app.db.session import SessionLocal
from app.models.evaluation import Evaluation, EvaluationComment
from app.services.sentiment import run_sentiment
from app.services.translation import translate_evaluation_comments


def parse_args():
    p = argparse.ArgumentParser(description="Import evaluation comments from CSV")
    p.add_argument("csv_file", help="Path to the CSV file (relative to /app or absolute)")
    p.add_argument(
        "--no-translate",
        action="store_true",
        help="Skip DeepL translation (comment_en will remain NULL)",
    )
    p.add_argument(
        "--no-sentiment",
        action="store_true",
        help="Skip sentiment scoring",
    )
    return p.parse_args()


def load_csv(path: Path) -> dict:
    """Read CSV and group rows by (idProfesor, idMateria, ciclo, anio)."""
    groups = defaultdict(list)
    total_rows = 0
    skipped = 0

    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            text = row.get("comments_texts", "").strip()
            if not text:
                skipped += 1
                continue
            key = (
                int(row["idProfesor"]),
                row["idMateria"].strip(),
                int(row["ciclo"]),
                int(row["anio"]),
            )
            groups[key].append(text)
            total_rows += 1

    print(f"CSV loaded: {total_rows} comments in {len(groups)} evaluation groups "
          f"({skipped} empty rows skipped)")
    return groups


def code_prefix(id_materia: str) -> str:
    """Extract 2-char department prefix from idMateria, e.g. 'BE2001 - 10' → 'BE'."""
    return id_materia[:2].upper()


def main():
    args = parse_args()
    csv_path = Path(args.csv_file)
    if not csv_path.is_absolute():
        csv_path = Path("/app") / csv_path
    if not csv_path.exists():
        print(f"Error: file not found: {csv_path}", file=sys.stderr)
        sys.exit(1)

    groups = load_csv(csv_path)

    db = SessionLocal()
    saved_ids = []
    skipped_groups = 0
    # Sequential number for CSV-imported evaluations (no evaluation number in CSV)
    next_number = (db.query(Evaluation).count() or 0) + 1

    try:
        for (id_profesor, id_materia, ciclo, anio), comments in groups.items():
            prefix = code_prefix(id_materia)

            # Dedup: skip if an evaluation with the same attributes already exists
            existing = (
                db.query(Evaluation)
                .filter(Evaluation.job_id == f"csv:{id_materia}:{id_profesor}:{ciclo}:{anio}")
                .first()
            )
            if existing:
                print(f"  [skip] Already imported: profesor={id_profesor} "
                      f"materia={id_materia} ciclo={ciclo} anio={anio}")
                skipped_groups += 1
                continue

            evaluation = Evaluation(
                job_id=f"csv:{id_materia}:{id_profesor}:{ciclo}:{anio}",
                number=next_number,
                code_prefix=prefix,
                total=0,
                cycle=ciclo,
                year=anio,
            )
            next_number += 1
            db.add(evaluation)
            db.flush()  # get evaluation.id

            for text in comments:
                db.add(EvaluationComment(evaluation_id=evaluation.id, comment=text))

            db.commit()
            saved_ids.append(evaluation.id)

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    print(f"\nInserted {len(saved_ids)} evaluations, skipped {skipped_groups} duplicates.")

    if not saved_ids:
        print("Nothing to process.")
        return

    # ── Translate ──────────────────────────────────────────────────────────────
    if not args.no_translate:
        print(f"\nTranslating comments for {len(saved_ids)} evaluations...")
        for i, eid in enumerate(saved_ids, 1):
            translate_evaluation_comments(eid)
            print(f"  [{i}/{len(saved_ids)}] translated evaluation {eid}")
    else:
        print("\nSkipping translation (--no-translate).")

    # ── Sentiment ──────────────────────────────────────────────────────────────
    if not args.no_sentiment:
        print(f"\nScoring sentiment for {len(saved_ids)} evaluations...")
        for i, eid in enumerate(saved_ids, 1):
            run_sentiment(eid)
            print(f"  [{i}/{len(saved_ids)}] scored evaluation {eid}")
    else:
        print("\nSkipping sentiment scoring (--no-sentiment).")

    print("\nDone.")


if __name__ == "__main__":
    main()
