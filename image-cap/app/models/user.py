from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(6), primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[str] = mapped_column(String(500), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    organizations: Mapped[list[UserOrganization]] = relationship(
        "UserOrganization", back_populates="user", cascade="all, delete-orphan"
    )
    sent_team_invitations: Mapped[list[TeamInvitation]] = relationship(
        "TeamInvitation",
        back_populates="inviter",
        foreign_keys="TeamInvitation.inviter_id",
        cascade="all, delete-orphan",
    )
    accepted_team_invitations: Mapped[list[TeamInvitation]] = relationship(
        "TeamInvitation",
        back_populates="accepted_by_user",
        foreign_keys="TeamInvitation.accepted_by",
    )
    password_histories: Mapped[list[PasswordHistory]] = relationship(
        "PasswordHistory",
        back_populates="user",
        cascade="all, delete-orphan",
    )


class Organization(Base):
    __tablename__ = "organizations"
    __table_args__ = (UniqueConstraint("nickname", "org_type", name="uq_org_nickname_type"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nickname: Mapped[str] = mapped_column(String(100), nullable=False)
    org_type: Mapped[str] = mapped_column(String(30), nullable=False)
    member_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    members: Mapped[list[UserOrganization]] = relationship(
        "UserOrganization", back_populates="organization", cascade="all, delete-orphan"
    )
    invitations: Mapped[list[TeamInvitation]] = relationship(
        "TeamInvitation", back_populates="organization", cascade="all, delete-orphan"
    )


class UserOrganization(Base):
    __tablename__ = "user_organizations"
    __table_args__ = (UniqueConstraint("user_id", "organization_id", name="uq_user_org_membership"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    joined_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    user: Mapped[User] = relationship("User", back_populates="organizations")
    organization: Mapped[Organization] = relationship("Organization", back_populates="members")


class TeamInvitation(Base):
    __tablename__ = "team_invitations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    token: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    inviter_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.utcnow() + timedelta(days=7)
    )
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    accepted_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    organization: Mapped[Organization] = relationship("Organization", back_populates="invitations")
    inviter: Mapped[User] = relationship(
        "User", back_populates="sent_team_invitations", foreign_keys=[inviter_id]
    )
    accepted_by_user: Mapped[User | None] = relationship(
        "User", back_populates="accepted_team_invitations", foreign_keys=[accepted_by]
    )


class PasswordHistory(Base):
    __tablename__ = "password_histories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    user: Mapped[User] = relationship("User", back_populates="password_histories")
