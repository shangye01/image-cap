from fastapi import APIRouter, HTTPException
from ..utils.security import hash_password, verify_password
from ..utils.jwt import create_access_token
from ..config import supabase  # 导入 supabase 客户端

router = APIRouter(prefix="/auth")


# 注册
@router.post("/register")
def register(data: dict):
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        raise HTTPException(400, "参数不完整")

    # 改成 "user"（单数）
    result = supabase.table("user").select("*").eq("username", username).execute()
    if result.data:
        raise HTTPException(400, "用户名已存在")

    # 改成 "user"
    user_data = {
        "username": username,
        "password_hash": hash_password(password)
    }
    supabase.table("user").insert(user_data).execute()

    return {"message": "注册成功"}


# 登录
@router.post("/login")
def login(data: dict):
    username = data.get("username")
    password = data.get("password")

    # 改成 "user"
    result = supabase.table("user").select("*").eq("username", username).execute()
    user = result.data[0] if result.data else None

    if not user or not verify_password(password, user["password_hash"]):
        raise HTTPException(401, "用户名或密码错误")

    token = create_access_token({"user_id": user["id"]})

    return {
        "access_token": token,
        "user": {
            "id": user["id"],
            "username": user["username"]
        }
    }