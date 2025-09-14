from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./legend_room.db")

engine = create_engine(DATABASE_URL, echo=False, future=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

def get_db():
    """
    Dependency for FastAPI: yields a database session, and closes it afterwards.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
