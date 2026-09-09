from app.infrastructure.db import Base
from sqlalchemy import ARRAY, Boolean, Column, Integer, String, Text, true


class Problem(Base):
    __tablename__ = "problem_bank"

    id = Column(Integer, primary_key=True)
    seed_key = Column(String, unique=True, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default=true())
    title = Column(String, index=True, nullable=False)
    difficulty = Column(Integer, index=True)  # 1=Easy,2=Medium,3=Hard
    categories = Column(ARRAY(String))
    description = Column(Text)
    test_cases = Column(Text)  # JSON string
