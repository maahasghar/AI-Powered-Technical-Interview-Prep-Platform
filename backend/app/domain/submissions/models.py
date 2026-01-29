from app.infrastructure.db import Base
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    problem_id = Column(
        Integer, ForeignKey("problem_bank.id"), index=True, nullable=False
    )
    code = Column(Text, nullable=False)
    language = Column(String, nullable=False)  # python, javascript, java, etc.
    status = Column(
        String, default="pending"
    )  # pending, accepted, rejected, runtime_error, time_limit_exceeded
    result = Column(Text)  # JSON string with test results
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
