# connection.py
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite:///./graph.db"

# SQLite configuration for thread safety
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # Allow cross-thread access
    pool_pre_ping=True,  # Verify connections before using them
)

# Enable foreign keys for SQLite
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
Base = declarative_base()