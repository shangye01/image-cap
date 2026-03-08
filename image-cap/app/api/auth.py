from fastapi import APIRouter, HTTPException
from pathlib import Path
import sqlite3

from ..utils.security import hash_password, verify_password
from ..utils.jwt import create_access_token
from ..config import supabase
router = APIRouter(prefix="/auth")

DB_PATH = Path(__file__).resolve().parents[2] / "test.db"


def _ensure_local_user_table() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL
            )
            """
        )
        conn.commit()


def _get_user_by_username(username: str):
    if supabase is not None:
        result = supabase.table("user").select("*").eq("username", username).execute()
        return result.data[0] if result.data else None

    _ensure_local_user_table()
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT id, username, password_hash FROM user WHERE username = ?",
            (username,),
        ).fetchone()
        return dict(row) if row else None


def _create_user(username: str, password_hash_value: str):
    if supabase is not None:
        return supabase.table("user").insert({
            "username": username,
            "password_hash": password_hash_value,
        }).execute()

    _ensure_local_user_table()
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            "INSERT INTO user (username, password_hash) VALUES (?, ?)",
            (username, password_hash_value),
        )
        conn.commit()
        return {"data": [{"id": cursor.lastrowid, "username": username}]}

# 注册
@router.post("/register")
def register(data: dict):
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        raise HTTPException(400, "参数不完整")

    # 改成 "user"（单数）
    user = _get_user_by_username(username)
    if user:
        raise HTTPException(400, "用户名已存在")

    # 改成 "user"
    _create_user(username, hash_password(password))

    return {"message": "注册成功"}


# 登录
@router.post("/login")
def login(data: dict):
    username = data.get("username")
    password = data.get("password")

    # 改成 "user"
    if not username or not password:
        raise HTTPException(400, "参数不完整")

    user = _get_user_by_username(username)

    if not user or not verify_password(password, user["password_hash"]):
        raise HTTPException(401, "用户名或密码错误")

    token = create_access_token({"user_id": user["id"]})

    return {
        "access_token": token,
        "user": {
            "id": user["id"],
            "username": user["username"],
        },
    }