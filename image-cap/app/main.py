from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from app.api import auth
from app.db.base import get_db

app = FastAPI()

# 前端跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发时允许所有
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router)

# 测试接口
@app.get("/")
def index():
    return {"message": "后端启动成功"}
