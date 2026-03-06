# database.py (简化版，暂时不用SQLAlchemy避免复杂依赖)
# 如果你暂时不需要复杂的数据库操作，可以先注释掉这个文件的内容
# 或者只保留模型定义，不要导入app
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Float, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

Base = declarative_base()

# 只保留模型定义，不导入app
class Task(Base):
    __tablename__ = "tasks"
    id = Column(String, primary_key=True)
    image_url = Column(String, nullable=False)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)

class Annotation(Base):
    __tablename__ = "annotations"
    id = Column(String, primary_key=True)
    task_id = Column(String, ForeignKey("tasks.id"))
    label = Column(String, nullable=False)
    x = Column(Float)
    y = Column(Float)
    width = Column(Float)
    height = Column(Float)