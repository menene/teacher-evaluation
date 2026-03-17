from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, SmallInteger, String, Text
from sqlalchemy.orm import relationship

from app.db.session import Base


class SentimentLabel(Base):
    __tablename__ = "sentiment_labels"

    id    = Column(SmallInteger, primary_key=True)
    label = Column(String(20), nullable=False, unique=True)

    comments = relationship("EvaluationComment", back_populates="sentiment")


class Topic(Base):
    __tablename__ = "topics"

    id         = Column(Integer, primary_key=True, index=True)
    keywords   = Column(Text, nullable=False)   # JSON array string
    weight     = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    comments = relationship("EvaluationComment", back_populates="topic")


class Evaluation(Base):
    __tablename__ = "evaluations"

    id          = Column(Integer, primary_key=True, index=True)
    job_id      = Column(String(36), nullable=True, index=True)
    number      = Column(Integer, nullable=False)
    code_prefix = Column(String(2), nullable=False)
    total       = Column(SmallInteger, nullable=False)   # 0–100
    cycle       = Column(Integer, nullable=False)
    year        = Column(SmallInteger, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    comments = relationship("EvaluationComment", back_populates="evaluation", cascade="all, delete-orphan")


class EvaluationComment(Base):
    __tablename__ = "evaluation_comments"

    id                 = Column(Integer, primary_key=True, index=True)
    evaluation_id      = Column(Integer, ForeignKey("evaluations.id", ondelete="CASCADE"), nullable=False)
    comment               = Column(Text, nullable=False)
    comment_en            = Column(Text, nullable=True)
    comment_preprocessed  = Column(Text, nullable=True)
    sentiment_compound    = Column(Float, nullable=True)
    sentiment_label_id    = Column(SmallInteger, ForeignKey("sentiment_labels.id", ondelete="SET NULL"), nullable=True)
    topic_id              = Column(Integer, ForeignKey("topics.id", ondelete="SET NULL"), nullable=True)

    evaluation = relationship("Evaluation", back_populates="comments")
    sentiment  = relationship("SentimentLabel", back_populates="comments")
    topic      = relationship("Topic", back_populates="comments")
