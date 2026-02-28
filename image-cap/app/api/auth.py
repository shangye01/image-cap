from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.utils.security import hash_password, verify_password
from app.models.user import User
from app.utils.jwt import create_access_token
from app.db.base import get_db

router = APIRouter(prefix="/auth")

# 注册
@router.post("/register")
def register(data: dict, db: Session = Depends(get_db)):
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        raise HTTPException(400, "参数不完整")

    exists = db.query(User).filter(User.username == username).first()
    if exists:
        raise HTTPException(400, "用户名已存在")

    user = User(
        username=username,
        password_hash=hash_password(password)
    )

    db.add(user)
    db.commit()

    return {"message": "注册成功"}

# 登录
@router.post("/login")
def login(data: dict, db: Session = Depends(get_db)):
    username = data.get("username")
    password = data.get("password")

    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(401, "用户名或密码错误")

    token = create_access_token({"user_id": user.id})

    return {
        "access_token": token,
        "user": {
            "id": user.id,
            "username": user.username
        }
    }
