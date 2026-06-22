"""
database.py
-------------------------------------------------
Single source of truth for SQLAlchemy engine, session, and Base.
Import Base from HERE everywhere else (never redefine it elsewhere),
otherwise you'll hit the "Table already defined" / declarative_base
conflict you ran into before in Proctor Exam.
-------------------------------------------------
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# SQL Server Connection String
DATABASE_URL = (
    "mssql+pyodbc://sa:1234@DESKTOP-P6IQ0B6\\SQLEXPRESS/OnlineMedicalStore"
    "?driver=ODBC+Driver+17+for+SQL+Server"
)

engine = create_engine(DATABASE_URL, echo=False)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def get_db():
    """Dependency used in every route that needs DB access."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

from sqlalchemy import text

if __name__ == "__main__":
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT @@VERSION"))
            print("✅ Database Connected Successfully!")
            print(result.scalar())
    except Exception as e:
        print("❌ Database Connection Failed!")
        print(e)