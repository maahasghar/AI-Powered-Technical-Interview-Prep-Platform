from app.core.config import settings
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from collections.abc import Generator
from sqlalchemy.orm import Session

#The engine is SQLAlchemy’s connection manager. It connects to PostgreSQL
engine = create_engine(settings.DATABASE_URL, future=True, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)

#describes your database models and tables
Base = declarative_base()


class Database:
    def __init__(self, session: Session):
        self.session = session

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

#create a dependency to get the database session
def get_db_session() -> Generator[Session, None, None]:
    db = SessionLocal()

    try:
        yield db
    except Exception:
        #rollback the unfinished transaction in case of an exception to avoid leaving the session in a bad state
        db.rollback()
        raise
    finally:
        db.close()
