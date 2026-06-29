"""SQLAlchemy engine + session. SQLite now; swap DATABASE_URL for Postgres later
without touching business logic (that's the point of using the ORM)."""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from .config import settings

# Ensure the sqlite folder exists (e.g. ./data/app.db)
if settings.database_url.startswith("sqlite:///"):
    db_path = settings.database_url.replace("sqlite:///", "", 1)
    folder = os.path.dirname(db_path)
    if folder:
        os.makedirs(folder, exist_ok=True)

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
