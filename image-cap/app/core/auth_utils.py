# app/core/auth_utils.py
import time
from datetime import datetime
from typing import Optional

from jose import jwt, ExpiredSignatureError
from app.utils.jwt import ALGORITHM, SECRET_KEY
from app.db.session import SessionLocal
from app.models import User


def _resolve_user_id_from_token(authorization: str | None) -> str | None:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("user_id")
    except Exception:
        return None


def _resolve_ws_username(token: str | None) -> str | None:
    if not token:
        print("[WS_AUTH] Token 为空")
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        print(
            f"[WS_AUTH] Token 解码成功: user_id={payload.get('user_id')}, exp={payload.get('exp')}, now={time.time()}")

        user_id = payload.get("user_id")
        if not user_id:
            print("[WS_AUTH] Token 缺少 user_id")
            return None

        # 检查过期 — 使用 jwt.decode 已经会自动验证 exp
        # 如果执行到这里，说明 token 未过期
        # 但为了安全，再手动检查一次
        exp = payload.get("exp")
        now = time.time()
        if exp and exp < now:
            print(f"[WS_AUTH] Token 已过期! exp={exp}, now={now}, 已过期 {now - exp:.0f} 秒")
            return None

        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                print(f"[WS_AUTH] 找到用户: {user.username}")
                return user.username
            else:
                print(f"[WS_AUTH] 用户不存在: user_id={user_id}")
                return None
        finally:
            db.close()

    except ExpiredSignatureError:
        print("[WS_AUTH] JWT 过期异常 (ExpiredSignatureError)")
        return None
    except jwt.JWTError as e:
        print(f"[WS_AUTH] JWT 错误: {e}")
        return None
    except Exception as e:
        print(f"[WS_AUTH] 未知错误: {e}")
        return None