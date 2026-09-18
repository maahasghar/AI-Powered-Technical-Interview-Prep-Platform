from app.infrastructure.db import Base
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.sql import func


class Feedback(Base):
    __tablename__ = "submission_feedback"
    __table_args__ = (
        UniqueConstraint("submission_id", "stage", name="uq_feedback_stage"),
    )

    id = Column(Integer, primary_key=True)
    submission_id = Column(
        Integer,
        ForeignKey("submissions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stage = Column(String, nullable=False)
    status = Column(
        String, nullable=False, default="QUEUED", server_default="QUEUED", index=True
    )
    payload = Column(Text, nullable=True)
    execution_id = Column(String, nullable=True)
    provider = Column(String, nullable=True)
    model = Column(String, nullable=True)
    prompt_version = Column(String, nullable=True)
    schema_version = Column(String, nullable=True)
    source = Column(String, nullable=True)
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    estimated_cost_usd = Column(String, nullable=True)
    generation_ms = Column(Integer, nullable=True)
    attempts = Column(Integer, nullable=True)
    error_type = Column(String, nullable=True)
    generated_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
