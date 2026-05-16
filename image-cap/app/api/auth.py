from __future__ import annotations

import base64
import os
import random
import secrets
from html import escape
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from jose import jwt
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..config import supabase
from ..core.password_policy import RECENT_PASSWORD_HISTORY_LIMIT, validate_password_policy
from ..db.session import get_db
from ..models import Organization, PasswordHistory, TeamInvitation, User, UserOrganization
from ..utils.jwt import ALGORITHM, SECRET_KEY, create_access_token
from ..utils.security import hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])

DEFAULT_ORG_TYPES = {"个人", "团队"}
AVATAR_BUCKET = os.getenv("SUPABASE_AVATAR_BUCKET", "avatars")
CAPTCHA_EXPIRE_MINUTES = 5
CAPTCHA_LENGTH = 4
CAPTCHA_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CAPTCHA_STORE: dict[str, dict[str, Any]] = {}
DEFAULT_AVATAR_SVGS = [
    ("avatar-1.svg", "#6366f1", "A"),
    ("avatar-2.svg", "#0ea5e9", "B"),
    ("avatar-3.svg", "#10b981", "C"),
    ("avatar-4.svg", "#f59e0b", "D"),
]


class RegisterRequest(BaseModel):
    username: str = Field(min_length=2, max_length=50)
    password: str = Field(min_length=8, max_length=128)
    organization_nickname: str | None = Field(default=None, max_length=100)
    organization_type: str | None = Field(default="个人", max_length=30)


class LoginRequest(BaseModel):
    username: str = Field(min_length=2, max_length=50)
    password: str = Field(min_length=6, max_length=128)
    captcha_id: str = Field(min_length=8, max_length=64)
    captcha_code: str = Field(min_length=4, max_length=10)


class CaptchaResponse(BaseModel):
    captcha_id: str
    image_data: str
    expires_in: int


class LogoutRequest(BaseModel):
    username: str | None = None


class UsernameUpdateRequest(BaseModel):
    username: str = Field(min_length=2, max_length=50)


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=6, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class AccountDeleteRequest(BaseModel):
    password: str = Field(min_length=6, max_length=128)


class OrganizationCreateRequest(BaseModel):
    organization_nickname: str = Field(min_length=2, max_length=100)
    organization_type: str = Field(default="团队", max_length=30)


class TeamInviteCreateRequest(BaseModel):
    organization_nickname: str = Field(min_length=1, max_length=100)


class TeamMemberOut(BaseModel):
    id: str
    name: str
    role: str
    joined_at: str | None = None


class OrganizationMemberListResponse(BaseModel):
    organization_nickname: str
    members: list[TeamMemberOut]



def _utc_now() -> datetime:
    return datetime.utcnow()


def _format_dt(value: datetime | None) -> str | None:
    return value.strftime("%Y-%m-%d %H:%M:%S") if value else None


def _assert_valid_password(password: str) -> None:
    try:
        validate_password_policy(password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _list_recent_password_histories(db: Session, user_id: str, limit: int = RECENT_PASSWORD_HISTORY_LIMIT) -> list[PasswordHistory]:
    stmt = (
        select(PasswordHistory)
        .where(PasswordHistory.user_id == user_id)
        .order_by(PasswordHistory.created_at.desc(), PasswordHistory.id.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt).all())


def _seed_current_password_history(db: Session, user: User) -> None:
    latest_history = db.scalar(
        select(PasswordHistory)
        .where(PasswordHistory.user_id == user.id)
        .order_by(PasswordHistory.created_at.desc(), PasswordHistory.id.desc())
        .limit(1)
    )
    if latest_history and latest_history.password_hash == user.password_hash:
        return

    db.add(
        PasswordHistory(
            user_id=user.id,
            password_hash=user.password_hash,
            created_at=user.last_login_at or user.created_at or _utc_now(),
        )
    )
    db.flush()


def _assert_password_not_recently_used(db: Session, user: User, password: str) -> None:
    for history in _list_recent_password_histories(db, user.id):
        if verify_password(password, history.password_hash):
            raise HTTPException(
                status_code=400,
                detail=f"新密码不能与最近 {RECENT_PASSWORD_HISTORY_LIMIT} 次使用过的密码重复",
            )


def _record_password_history(db: Session, user_id: str, password_hash: str) -> None:
    db.add(PasswordHistory(user_id=user_id, password_hash=password_hash, created_at=_utc_now()))
    db.flush()

    histories = list(
        db.scalars(
            select(PasswordHistory)
            .where(PasswordHistory.user_id == user_id)
            .order_by(PasswordHistory.created_at.desc(), PasswordHistory.id.desc())
        ).all()
    )
    for stale_history in histories[RECENT_PASSWORD_HISTORY_LIMIT:]:
        db.delete(stale_history)


def _avatar_svg(fill: str, label: str) -> bytes:
    return f"""<svg xmlns='http://www.w3.org/2000/svg' width='256' height='256' viewBox='0 0 256 256'>
<rect width='256' height='256' rx='64' fill='{fill}' />
<text x='50%' y='54%' dominant-baseline='middle' text-anchor='middle'
      font-family='Arial, sans-serif' font-size='120' font-weight='700' fill='white'>{label}</text>
</svg>""".encode("utf-8")


def _cleanup_expired_captchas() -> None:
    now = _utc_now()
    expired_ids = [
        captcha_id
        for captcha_id, item in CAPTCHA_STORE.items()
        if item.get("expires_at") is None or item["expires_at"] <= now
    ]
    for captcha_id in expired_ids:
        CAPTCHA_STORE.pop(captcha_id, None)


def _build_captcha_svg(code: str) -> bytes:
    line_fragments = []
    for _ in range(6):
        x1 = random.randint(8, 152)
        y1 = random.randint(8, 52)
        x2 = random.randint(8, 152)
        y2 = random.randint(8, 52)
        color = random.choice(["#cbd5e1", "#bfdbfe", "#ddd6fe", "#fecaca"])
        line_fragments.append(
            f"<line x1='{x1}' y1='{y1}' x2='{x2}' y2='{y2}' stroke='{color}' stroke-width='1.5' />"
        )

    text_fragments = []
    for index, char in enumerate(code):
        x = 22 + index * 28 + random.randint(-2, 2)
        y = 35 + random.randint(-3, 4)
        rotate = random.randint(-18, 18)
        color = random.choice(["#0f172a", "#1d4ed8", "#7c3aed", "#be123c"])
        text_fragments.append(
            f"<text x='{x}' y='{y}' transform='rotate({rotate} {x} {y})' "
            f"font-family='Arial, sans-serif' font-size='24' font-weight='700' fill='{color}'>{escape(char)}</text>"
        )

    svg = f"""
<svg xmlns='http://www.w3.org/2000/svg' width='160' height='60' viewBox='0 0 160 60'>
  <rect width='160' height='60' rx='12' fill='#f8fafc' />
  <rect x='1' y='1' width='158' height='58' rx='11' fill='none' stroke='#cbd5e1' />
  {''.join(line_fragments)}
  {''.join(text_fragments)}
</svg>
""".strip()
    return svg.encode("utf-8")


def _issue_captcha() -> CaptchaResponse:
    _cleanup_expired_captchas()
    code = "".join(secrets.choice(CAPTCHA_ALPHABET) for _ in range(CAPTCHA_LENGTH))
    captcha_id = secrets.token_urlsafe(16)
    expires_at = _utc_now() + timedelta(minutes=CAPTCHA_EXPIRE_MINUTES)
    CAPTCHA_STORE[captcha_id] = {"code": code, "expires_at": expires_at}
    image_data = "data:image/svg+xml;base64," + base64.b64encode(_build_captcha_svg(code)).decode("ascii")
    return CaptchaResponse(
        captcha_id=captcha_id,
        image_data=image_data,
        expires_in=CAPTCHA_EXPIRE_MINUTES * 60,
    )


def _verify_captcha(captcha_id: str, captcha_code: str) -> None:
    _cleanup_expired_captchas()
    captcha = CAPTCHA_STORE.pop(captcha_id, None)
    if not captcha:
        raise HTTPException(status_code=400, detail="验证码错误或已过期，请刷新后重试")

    expected_code = str(captcha.get("code") or "").strip().upper()
    submitted_code = captcha_code.strip().upper()
    if not submitted_code or submitted_code != expected_code:
        raise HTTPException(status_code=400, detail="验证码错误或已过期，请刷新后重试")


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


def _get_user_query():
    return select(User).options(
        selectinload(User.organizations).selectinload(UserOrganization.organization)
    )

def _get_user_by_username(db: Session, username: str) -> User | None:
    return db.scalar(_get_user_query().where(User.username == username))



def _get_user_by_id(db: Session, user_id: str) -> User | None:
    return db.scalar(_get_user_query().where(User.id == user_id))


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


def _get_organization_by_name(db: Session, nickname: str, org_type: str | None = None) -> Organization | None:
    stmt = select(Organization).where(Organization.nickname == nickname)
    if org_type:
        stmt = stmt.where(Organization.org_type == org_type)
    return db.scalar(stmt)


def _ensure_organization(db: Session, nickname: str, org_type: str, joined_at: datetime) -> Organization:
    organization = _get_organization_by_name(db, nickname, org_type)
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


def _join_organization(db: Session, user: User, organization: Organization, joined_at: datetime) -> bool:
    stmt = select(UserOrganization).where(
        UserOrganization.user_id == user.id,
        UserOrganization.organization_id == organization.id,
    )
    membership = db.scalar(stmt)
    if membership:
        return False

    db.add(UserOrganization(user_id=user.id, organization_id=organization.id, joined_at=joined_at))
    db.flush()
    member_count = db.scalar(
        select(func.count(UserOrganization.id)).where(UserOrganization.organization_id == organization.id)
    )
    organization.member_count = int(member_count or 0)
    return True


def _sync_organization_member_count(db: Session, organization_id: int) -> None:
    organization = db.get(Organization, organization_id)
    if not organization:
        return

    member_count = db.scalar(
        select(func.count(UserOrganization.id)).where(UserOrganization.organization_id == organization_id)
    )
    organization.member_count = int(member_count or 0)
    if organization.member_count <= 0:
        db.delete(organization)
    db.flush()


def _remove_membership(db: Session, user_id: str, organization: Organization) -> None:
    membership = db.scalar(
        select(UserOrganization).where(
            UserOrganization.user_id == user_id,
            UserOrganization.organization_id == organization.id,
        )
    )
    if not membership:
        raise HTTPException(status_code=404, detail="你尚未加入该团队")

    db.delete(membership)
    db.flush()
    _sync_organization_member_count(db, organization.id)


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

def _require_current_user(db: Session, authorization: str | None) -> User:
    user_id = _resolve_user_id_from_token(authorization)
    if not user_id:
        raise HTTPException(status_code=401, detail="未登录或 token 无效")

    user = _get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


def _serialize_invitation(invitation: TeamInvitation) -> dict[str, Any]:
    organization = invitation.organization
    inviter = invitation.inviter
    return {
        "token": invitation.token,
        "organization_nickname": organization.nickname,
        "organization_type": organization.org_type,
        "organization_created_at": _format_dt(organization.created_at),
        "inviter_id": inviter.id,
        "inviter_name": inviter.username,
        "invite_link": f"/invite/{invitation.token}",
        "created_at": _format_dt(invitation.created_at),
        "expires_at": _format_dt(invitation.expires_at),
        "accepted_user_ids": [member.user_id for member in organization.members if member.user_id != inviter.id],
        "accepted_members": [
            {"user_id": member.user.id, "username": member.user.username}
            for member in organization.members
            if member.user.id != inviter.id
        ],
        "accepted_at": _format_dt(invitation.accepted_at),
        "accepted_by": invitation.accepted_by,
    }


def _serialize_members(organization: Organization) -> list[dict[str, Any]]:
    ordered = sorted(organization.members, key=lambda item: item.joined_at)
    owner_user_id = ordered[0].user_id if ordered else None
    return [
        {
            "id": membership.user.id,
            "name": membership.user.username,
            "role": "管理员" if membership.user_id == owner_user_id else "团队成员",
            "joined_at": _format_dt(membership.joined_at),
        }
        for membership in ordered
    ]



@router.post("/register")
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    username = data.username.strip()
    if _get_user_by_username(db, username):
        raise HTTPException(status_code=409, detail="用户名已存在")
    _assert_valid_password(data.password)

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
    _record_password_history(db, user.id, user.password_hash)

    default_organization = _ensure_organization(db, f"{username}的个人团队", "个人", joined_at)
    _join_organization(db, user, default_organization, joined_at)
    db.commit()

    fresh_user = _get_user_by_id(db, user.id)
    return {"message": "注册成功", "user": _serialize_user(fresh_user)}



@router.get("/captcha", response_model=CaptchaResponse)
def get_captcha():
    return _issue_captcha()


@router.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    _verify_captcha(data.captcha_id, data.captcha_code)
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
def logout(
    data: LogoutRequest,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
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
    user = _require_current_user(db, authorization)
    return {"user": _serialize_user(user)}


@router.put("/me/username")
def update_username(
    payload: UsernameUpdateRequest,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    user = _require_current_user(db, authorization)
    username = payload.username.strip()
    if username != user.username and _get_user_by_username(db, username):
        raise HTTPException(status_code=409, detail="用户名已存在")

    user.username = username
    db.commit()
    fresh_user = _get_user_by_id(db, user.id)
    return {"message": "用户名已更新", "user": _serialize_user(fresh_user)}


@router.put("/me/password")
def change_password(
    payload: PasswordChangeRequest,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    user = _require_current_user(db, authorization)
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=401, detail="当前密码不正确")
    if payload.current_password == payload.new_password:
        raise HTTPException(status_code=400, detail="新密码不能与当前密码相同")
    _assert_valid_password(payload.new_password)
    _seed_current_password_history(db, user)
    _assert_password_not_recently_used(db, user, payload.new_password)

    user.password_hash = hash_password(payload.new_password)
    _record_password_history(db, user.id, user.password_hash)
    db.commit()
    return {"message": "密码已更新"}


@router.delete("/me")
def delete_account(
    payload: AccountDeleteRequest,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    user = _require_current_user(db, authorization)
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="密码不正确")

    organization_ids = [membership.organization_id for membership in user.organizations]
    db.delete(user)
    db.flush()
    for organization_id in organization_ids:
        _sync_organization_member_count(db, organization_id)
    db.commit()
    return {"message": "账户已注销"}


@router.post("/organizations")
def create_organization(
    payload: OrganizationCreateRequest,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    user = _require_current_user(db, authorization)
    nickname = payload.organization_nickname.strip()
    org_type = (payload.organization_type or "团队").strip() or "团队"
    if org_type != "团队":
        raise HTTPException(status_code=400, detail="手动创建的组织仅支持团队类型")

    joined_at = _utc_now()
    organization = _get_organization_by_name(db, nickname, org_type)
    if organization:
        raise HTTPException(status_code=409, detail="该团队名称已存在")

    organization = _ensure_organization(db, nickname, org_type, joined_at)
    _join_organization(db, user, organization, joined_at)
    db.commit()

    fresh_user = _get_user_by_id(db, user.id)
    return {
        "message": "团队创建成功",
        "organization": {
            "organization_nickname": organization.nickname,
            "organization_type": organization.org_type,
            "joined_at": _format_dt(joined_at),
            "member_count": organization.member_count,
            "organization_created_at": _format_dt(organization.created_at),
        },
        "user": _serialize_user(fresh_user),
    }


@router.get("/organizations/{organization_nickname}/members", response_model=OrganizationMemberListResponse)
def list_organization_members(
    organization_nickname: str,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    user = _require_current_user(db, authorization)
    organization = db.scalar(
        select(Organization)
        .options(selectinload(Organization.members).selectinload(UserOrganization.user))
        .join(UserOrganization, UserOrganization.organization_id == Organization.id)
        .where(Organization.nickname == organization_nickname, UserOrganization.user_id == user.id)
    )
    if not organization:
        raise HTTPException(status_code=404, detail="未找到当前组织或你尚未加入该组织")

    return {
        "organization_nickname": organization.nickname,
        "members": _serialize_members(organization),
    }


@router.delete("/organizations/{organization_nickname}/members/me")
def leave_organization(
    organization_nickname: str,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    user = _require_current_user(db, authorization)
    organization = db.scalar(
        select(Organization)
        .join(UserOrganization, UserOrganization.organization_id == Organization.id)
        .where(
            Organization.nickname == organization_nickname,
            UserOrganization.user_id == user.id,
        )
    )
    if not organization:
        raise HTTPException(status_code=404, detail="未找到当前团队或你尚未加入")
    if organization.org_type != "团队":
        raise HTTPException(status_code=400, detail="个人组织不支持退出")

    _remove_membership(db, user.id, organization)
    db.commit()
    fresh_user = _get_user_by_id(db, user.id)
    return {"message": f"已退出团队“{organization_nickname}”", "user": _serialize_user(fresh_user)}


@router.post("/team-invitations")
def create_team_invitation(
    payload: TeamInviteCreateRequest,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    user = _require_current_user(db, authorization)
    organization = db.scalar(
        select(Organization)
        .join(UserOrganization, UserOrganization.organization_id == Organization.id)
        .where(
            Organization.nickname == payload.organization_nickname.strip(),
            Organization.org_type == "团队",
            UserOrganization.user_id == user.id,
        )
    )
    if not organization:
        raise HTTPException(status_code=404, detail="团队不存在或你无权邀请成员")

    invitation = TeamInvitation(
        token=secrets.token_urlsafe(24),
        organization_id=organization.id,
        inviter_id=user.id,
        created_at=_utc_now(),
        expires_at=_utc_now() + timedelta(days=7),
    )
    db.add(invitation)
    db.commit()

    fresh_invitation = db.scalar(
        select(TeamInvitation)
        .options(
            selectinload(TeamInvitation.organization).selectinload(Organization.members).selectinload(UserOrganization.user),
            selectinload(TeamInvitation.inviter),
        )
        .where(TeamInvitation.id == invitation.id)
    )
    return _serialize_invitation(fresh_invitation)


@router.get("/team-invitations/{token}")
def get_team_invitation(token: str, db: Session = Depends(get_db)):
    invitation = db.scalar(
        select(TeamInvitation)
        .options(
            selectinload(TeamInvitation.organization).selectinload(Organization.members).selectinload(UserOrganization.user),
            selectinload(TeamInvitation.inviter),
        )
        .where(TeamInvitation.token == token)
    )
    if not invitation:
        raise HTTPException(status_code=404, detail="邀请链接不存在或已失效")
    return _serialize_invitation(invitation)


@router.post("/team-invitations/{token}/accept")
def accept_team_invitation(
    token: str,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    user = _require_current_user(db, authorization)
    invitation = db.scalar(
        select(TeamInvitation)
        .options(
            selectinload(TeamInvitation.organization).selectinload(Organization.members).selectinload(UserOrganization.user),
            selectinload(TeamInvitation.inviter),
        )
        .where(TeamInvitation.token == token)
    )
    if not invitation:
        raise HTTPException(status_code=404, detail="邀请链接不存在或已失效")
    if invitation.expires_at < _utc_now():
        raise HTTPException(status_code=400, detail="邀请链接已过期，请联系团队重新生成")

    already_joined = any(membership.user_id == user.id for membership in invitation.organization.members)
    if not already_joined:
        _join_organization(db, user, invitation.organization, _utc_now())
        invitation.accepted_at = _utc_now()
        invitation.accepted_by = user.id
        db.commit()
    else:
        db.commit()

    fresh_user = _get_user_by_id(db, user.id)
    fresh_invitation = db.scalar(
        select(TeamInvitation)
        .options(
            selectinload(TeamInvitation.organization).selectinload(Organization.members).selectinload(UserOrganization.user),
            selectinload(TeamInvitation.inviter),
        )
        .where(TeamInvitation.token == token)
    )

    return {
        "alreadyJoined": already_joined,
        "organization": {
            "organization_nickname": fresh_invitation.organization.nickname,
            "organization_type": fresh_invitation.organization.org_type,
            "joined_at": _format_dt(_utc_now()),
            "member_count": fresh_invitation.organization.member_count,
            "organization_created_at": _format_dt(fresh_invitation.organization.created_at),
        },
        "invitation": _serialize_invitation(fresh_invitation),
        "user": _serialize_user(fresh_user),
    }
