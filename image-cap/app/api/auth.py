from __future__ import annotations

import os
import random
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..config import supabase
from ..db.session import get_db
from ..models import Organization, User, UserOrganization
from ..utils.jwt import ALGORITHM, SECRET_KEY, create_access_token
from ..utils.security import hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])

DEFAULT_ORG_TYPES = {"个人", "团队"}
AVATAR_BUCKET = os.getenv("SUPABASE_AVATAR_BUCKET", "avatars")
DEFAULT_AVATAR_SVGS = [
    ("avatar-1.svg", "#6366f1", "A"),
    ("avatar-2.svg", "#0ea5e9", "B"),
    ("avatar-3.svg", "#10b981", "C"),
    ("avatar-4.svg", "#f59e0b", "D"),
]


class RegisterRequest(BaseModel):
    username: str = Field(min_length=2, max_length=50)
    password: str = Field(min_length=6, max_length=128)
    organization_nickname: str | None = Field(default=None, max_length=100)
    organization_type: str | None = Field(default="个人", max_length=30)


class LoginRequest(BaseModel):
    username: str = Field(min_length=2, max_length=50)
    password: str = Field(min_length=6, max_length=128)


class LogoutRequest(BaseModel):
    username: str | None = None


def _utc_now() -> datetime:
    return datetime.utcnow()


def _format_dt(value: datetime | None) -> str | None:
    return value.strftime("%Y-%m-%d %H:%M:%S") if value else None


def _avatar_svg(fill: str, label: str) -> bytes:
    return f"""<svg xmlns='http://www.w3.org/2000/svg' width='256' height='256' viewBox='0 0 256 256'>
<rect width='256' height='256' rx='64' fill='{fill}' />
<text x='50%' y='54%' dominant-baseline='middle' text-anchor='middle'
      font-family='Arial, sans-serif' font-size='120' font-weight='700' fill='white'>{label}</text>
</svg>""".encode("utf-8")


def _normalize_bucket_list(items: Any) -> list[Any]:
    if isinstance(items, list):
        return items
    if hasattr(items, "data") and isinstance(items.data, list):
        return items.data
    return []


def _storage_item_name(item: Any) -> str | None:
    if isinstance(item, dict):
        return item.get("name")
    return getattr(item, "name", None)


def ensure_auth_resources() -> None:
    if supabase is None:
        raise RuntimeError("Supabase 未配置，无法初始化认证存储资源。")

    try:
        bucket_items = _normalize_bucket_list(supabase.storage.list_buckets())
        bucket_names = {name for item in bucket_items if (name := _storage_item_name(item))}
        if AVATAR_BUCKET not in bucket_names:
            try:
                supabase.storage.create_bucket(AVATAR_BUCKET, options={"public": True})
            except Exception:
                pass

        storage = supabase.storage.from_(AVATAR_BUCKET)
        existing_files = [item for item in _normalize_bucket_list(storage.list()) if _storage_item_name(item)]
        if existing_files:
            return

        for filename, color, label in DEFAULT_AVATAR_SVGS:
            try:
                storage.upload(
                    filename,
                    _avatar_svg(color, label),
                    {"content-type": "image/svg+xml", "x-upsert": "true"},
                )
            except Exception:
                pass
    except Exception as exc:
        raise RuntimeError(f"初始化 Supabase Storage 失败: {exc}") from exc


def _pick_random_avatar() -> str:
    if supabase is None:
        raise HTTPException(status_code=500, detail="Supabase Storage 未配置，无法分配头像")

    try:
        ensure_auth_resources()
        files = _normalize_bucket_list(supabase.storage.from_(AVATAR_BUCKET).list())
        candidates = [name for item in files if (name := _storage_item_name(item)) and not name.startswith(".")]
        if not candidates:
            raise HTTPException(status_code=500, detail="Supabase Storage 中没有可用头像文件")
        return supabase.storage.from_(AVATAR_BUCKET).get_public_url(random.choice(candidates))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"从 Supabase Storage 获取头像失败: {exc}") from exc


def _generate_user_id(db: Session) -> str:
    while True:
        candidate = f"{random.randint(0, 999999):06d}"
        if db.get(User, candidate) is None:
            return candidate


def _get_user_by_username(db: Session, username: str) -> User | None:
    stmt = (
        select(User)
        .options(selectinload(User.organizations).selectinload(UserOrganization.organization))
        .where(User.username == username)
    )
    return db.scalar(stmt)


def _get_user_by_id(db: Session, user_id: str) -> User | None:
    stmt = (
        select(User)
        .options(selectinload(User.organizations).selectinload(UserOrganization.organization))
        .where(User.id == user_id)
    )
    return db.scalar(stmt)


def _serialize_user(user: User) -> dict[str, Any]:
    memberships = sorted(user.organizations, key=lambda item: item.joined_at)
    return {
        "id": user.id,
        "username": user.username,
        "avatar": user.avatar_url,
        "is_active": bool(user.is_active),
        "created_at": _format_dt(user.created_at),
        "last_login_at": _format_dt(user.last_login_at),
        "organizations": [
            {
                "organization_nickname": membership.organization.nickname,
                "organization_type": membership.organization.org_type,
                "joined_at": _format_dt(membership.joined_at),
                "member_count": membership.organization.member_count,
                "organization_created_at": _format_dt(membership.organization.created_at),
            }
            for membership in memberships
        ],
    }


def _ensure_organization(db: Session, nickname: str, org_type: str, joined_at: datetime) -> Organization:
    stmt = select(Organization).where(Organization.nickname == nickname, Organization.org_type == org_type)
    organization = db.scalar(stmt)
    if organization:
        return organization

    organization = Organization(
        nickname=nickname,
        org_type=org_type,
        member_count=1,
        created_at=joined_at,
    )
    db.add(organization)
    db.flush()
    return organization


def _join_organization(db: Session, user: User, organization: Organization, joined_at: datetime) -> None:
    stmt = select(UserOrganization).where(
        UserOrganization.user_id == user.id,
        UserOrganization.organization_id == organization.id,
    )
    membership = db.scalar(stmt)
    if membership:
        return

    db.add(UserOrganization(user_id=user.id, organization_id=organization.id, joined_at=joined_at))
    db.flush()
    member_count = db.scalar(
        select(func.count(UserOrganization.id)).where(UserOrganization.organization_id == organization.id)
    )
    organization.member_count = int(member_count or 0)


def _resolve_user_id_from_token(authorization: str | None) -> str | None:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None

    token = authorization.split(" ", 1)[1].strip()
    if not token:
        return None

    try:
        from jose import jwt

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("user_id")
    except Exception:
        return None

# 注册
@router.post("/register")
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    org_type = (data.organization_type or "个人").strip()
    if org_type not in DEFAULT_ORG_TYPES:
        raise HTTPException(status_code=400, detail="组织类型只支持个人或团队")

    username = data.username.strip()
    organization_nickname = (data.organization_nickname or f"{username}的组织").strip()
    joined_at = _utc_now()

    username = data.username.strip()
    organization_nickname = (data.organization_nickname or f"{username}的组织").strip()
    joined_at = _utc_now()

    user = User(
        id=_generate_user_id(db),
        username=username,
        password_hash=hash_password(data.password),
        avatar_url=_pick_random_avatar(),
        is_active=True,
        created_at=joined_at,
        last_login_at=joined_at,
    )
    db.add(user)
    db.flush()

    organization = _ensure_organization(db, organization_nickname, org_type, joined_at)
    _join_organization(db, user, organization, joined_at)
    db.commit()
    db.refresh(user)

    fresh_user = _get_user_by_id(db, user.id)
    return {"message": "注册成功", "user": _serialize_user(fresh_user)}


# 登录
@router.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = _get_user_by_username(db, data.username.strip())
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    user.is_active = True
    user.last_login_at = _utc_now()
    db.commit()

    fresh_user = _get_user_by_id(db, user.id)
    token = create_access_token({"user_id": fresh_user.id, "username": fresh_user.username})
    return {"access_token": token, "user": _serialize_user(fresh_user)}

    @router.post("/logout")
    def logout(data: LogoutRequest, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
        user_id = _resolve_user_id_from_token(authorization)
        if not user_id and data.username:
            user = _get_user_by_username(db, data.username.strip())
            user_id = user.id if user else None

    if user_id:
        user = _get_user_by_id(db, user_id)
        if user:
            user.is_active = False
            db.commit()
    return {"message": "退出成功"}

    @router.get("/me")
    def get_me(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
        user_id = _resolve_user_id_from_token(authorization)
        if not user_id:
            raise HTTPException(status_code=401, detail="未登录或 token 无效")

        user = _get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        return {"user": _serialize_user(user)}