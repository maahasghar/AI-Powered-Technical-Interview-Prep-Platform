from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.infrastructure.db import Base
from sqlalchemy import Column, Integer, String, Text, ARRAY


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, unique=True)
    full_name = Column(String)
    bio = Column(String)
    avatar_url = Column(String)