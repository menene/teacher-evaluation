"""
Evaluation upload and retrieval routes.
"""
import os
import uuid
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.evaluation import Evaluation
from app.models.job import Job
from app.services.pdf_parser import parse_pdf
from app.worker.tasks import process_pdf

router = APIRouter(prefix="/evaluations", tags=["evaluations"])

UPLOADS_DIR = "/app/uploads"


@router.post("/upload/analyze")
async def upload_analyze(files: List[UploadFile] = File(...)):
    """Parse PDFs and return extracted data without saving to DB."""
    results = []
    for file in files:
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail=f"{file.filename} is not a PDF")
        tmp_path = f"{UPLOADS_DIR}/preview_{uuid.uuid4().hex}.pdf"
        try:
            with open(tmp_path, "wb") as f:
                f.write(await file.read())
            evaluations = parse_pdf(tmp_path)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        results.append({"filename": file.filename, "evaluations": evaluations})
    return results


@router.post("/upload")
async def upload(files: List[UploadFile] = File(...), db: Session = Depends(get_db)):
    """Save PDFs to disk, create jobs, queue Celery pipeline. Returns job IDs immediately."""
    jobs_created = []

    for file in files:
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail=f"{file.filename} is not a PDF")

        job_id = str(uuid.uuid4())
        file_path = f"{UPLOADS_DIR}/{job_id}.pdf"

        with open(file_path, "wb") as f:
            f.write(await file.read())

        job = Job(id=job_id, filename=file.filename, status="pending")
        db.add(job)
        db.commit()

        process_pdf.delay(job_id, file_path)
        jobs_created.append({"job_id": job_id, "filename": file.filename})

    return jobs_created


@router.get("/")
def list_evaluations(db: Session = Depends(get_db)):
    rows = db.query(Evaluation).order_by(Evaluation.uploaded_at.desc()).all()
    return [
        {
            "id": e.id,
            "number": e.number,
            "code_prefix": e.code_prefix,
            "year": e.year,
            "cycle": e.cycle,
            "uploaded_at": e.uploaded_at,
        }
        for e in rows
    ]
