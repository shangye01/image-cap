from __future__ import annotations

import re


MIN_PASSWORD_LENGTH = 8
RECENT_PASSWORD_HISTORY_LIMIT = 3

LETTER_PATTERN = re.compile(r"[A-Za-z]")
DIGIT_PATTERN = re.compile(r"\d")
SPECIAL_PATTERN = re.compile(r"[^A-Za-z0-9]")

COMMON_WEAK_PASSWORDS = {
    "12345678",
    "123456789",
    "1234567890",
    "87654321",
    "00000000",
    "11111111",
    "aaaaaaaa",
    "abc12345",
    "abcd1234",
    "password",
    "password1",
    "password123",
    "qwertyui",
    "qwerty123",
    "admin123",
    "welcome123",
    "iloveyou",
}


def validate_password_policy(password: str) -> None:
    candidate = password or ""

    if len(candidate) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"密码长度至少 {MIN_PASSWORD_LENGTH} 位")

    if not LETTER_PATTERN.search(candidate):
        raise ValueError("密码至少包含一个字母")

    if not DIGIT_PATTERN.search(candidate):
        raise ValueError("密码至少包含一个数字")

    if candidate.lower() in COMMON_WEAK_PASSWORDS:
        raise ValueError("请勿使用常见弱密码")


def password_policy_hint() -> str:
    return (
        f"密码至少 {MIN_PASSWORD_LENGTH} 位，且必须包含字母和数字；"
        "可加入特殊符号提升安全性，请勿使用常见弱密码。"
    )


def has_special_character(password: str) -> bool:
    return bool(SPECIAL_PATTERN.search(password or ""))
