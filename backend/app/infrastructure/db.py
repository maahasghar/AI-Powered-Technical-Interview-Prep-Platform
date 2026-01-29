from app.core.config import settings
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

engine = create_engine(settings.DATABASE_URL, future=True, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)

Base = declarative_base()


class Database:
    def __init__(self):
        self.session = SessionLocal()

    def query(self, model):
        return self.session.query(model)

    def add(self, obj):
        self.session.add(obj)

    def commit(self):
        self.session.commit()

    def refresh(self, obj):
        self.session.refresh(obj)

    def delete(self, obj):
        self.session.delete(obj)

    def close(self):
        self.session.close()


def get_db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
