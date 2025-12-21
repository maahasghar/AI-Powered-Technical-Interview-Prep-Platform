from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.infrastructure.db import Base
from sqlalchemy import Column, Integer, String, Text, ARRAY

class Problem(Base):
    __tablename__ = "problem_bank"

    id = Column(Integer, primary_key=True)
    title = Column(String, index=True, nullable=False)
    difficulty = Column(Integer, index=True)  # 1=Easy,2=Medium,3=Hard
    categories = Column(ARRAY(String))
    description = Column(Text)
    test_cases = Column(Text)  # JSON string
