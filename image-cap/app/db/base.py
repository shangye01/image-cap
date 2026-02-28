from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.user import Base

# ↓↓↓ 改成你的真实 MySQL 信息 ↓↓↓
DATABASE_URL = (
    "mysql+pymysql://root6:123456@localhost:3306/root1?charset=utf8mb4"
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,     # 防止 MySQL 断线
    echo=True               # 开发阶段建议打开，能看到 SQL
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# 初始化表（只会创建不存在的表）
Base.metadata.create_all(bind=engine)

# FastAPI 依赖
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
