from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from app.db.session import Base


class Job(Base):
    __tablename__ = "jobs"

    id            = Column(String(36), primary_key=True)
    evaluation_id = Column(Integer, ForeignKey("evaluations.id", ondelete="SET NULL"), nullable=True)
    filename      = Column(String(255), nullable=False)
    status        = Column(String(20), nullable=False, default="pending")
    error         = Column(Text, nullable=True)
    notes         = Column(Text, nullable=True)  # JSON list of warning strings
    created_at    = Column(DateTime, default=datetime.utcnow)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
