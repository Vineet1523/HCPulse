from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"

class Settings(BaseSettings):
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/hcpulse"
    frontend_origin: str = "http://localhost:5173"
    model_config = SettingsConfigDict(env_file=ROOT_ENV, extra="ignore")

settings = Settings()
engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
