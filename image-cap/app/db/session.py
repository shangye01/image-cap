"""PostgreSQL session management for FastAPI.

Use SUPABASE_DB_URL in environment, for example:
postgresql+psycopg2://postgres:<password>@db.<project-ref>.supabase.co:5432/postgres
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=env_path)

DATABASE_URL = os.getenv("SUPABASE_DB_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "缺少 SUPABASE_DB_URL，请在 image-cap/.env 中配置 Supabase PostgreSQL 连接串。"
    )

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=1800,
)

# ✅ 关键修复：使用 expire_on_commit=True 确保每次查询都刷新
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    expire_on_commit=True,  # ✅ 改为 True，确保 commit 后对象过期，下次查询会重新加载
    bind=engine
)

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()