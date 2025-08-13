from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import os
from dotenv import load_dotenv

load_dotenv()

def get_sqlalchemy_database_url():
    """Convert Prisma DATABASE_URL format to SQLAlchemy format"""
    database_url = os.getenv("DATABASE_URL", "file:./database.db")
    
    # Convert Prisma format to SQLAlchemy format for SQLite
    if database_url.startswith("file:"):
        # Remove 'file:' and add 'sqlite:///' prefix
        db_file = database_url.replace("file:", "")
        if db_file.startswith("./"):
            db_file = db_file[2:]  # Remove './'
        return f"sqlite:///{db_file}"
    
    # Return as-is for other database types (PostgreSQL, MySQL, etc.)
    return database_url

DATABASE_URL = get_sqlalchemy_database_url()

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()