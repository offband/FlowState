from __future__ import annotations

import os
import secrets
from pathlib import Path

from .paths import TOKEN_ENV, token_path
from .store import ensure_home


def _make_private(path: Path) -> None:
    path.chmod(0o600)


def _write_token(path: Path, token: str) -> None:
    path.write_text(token + "\n", encoding="utf-8")
    _make_private(path)


def _read_existing_token(path: Path) -> str:
    _make_private(path)
    return path.read_text(encoding="utf-8").strip()


def ensure_token(home: Path | None = None) -> str:
    ensure_home(home)
    path = token_path(home)
    if path.exists():
        token = _read_existing_token(path)
        if token:
            return token
    token = secrets.token_urlsafe(32)
    _write_token(path, token)
    return token


def rotate_token(home: Path | None = None) -> str:
    ensure_home(home)
    token = secrets.token_urlsafe(32)
    path = token_path(home)
    _write_token(path, token)
    return token


def read_token(home: Path | None = None) -> str:
    configured = configured_token(home)
    if configured:
        return configured
    return ensure_token(home)


def configured_token(home: Path | None = None) -> str:
    env_token = os.environ.get(TOKEN_ENV)
    if env_token:
        return env_token
    path = token_path(home)
    if path.exists():
        return _read_existing_token(path)
    return ""


def verify_bearer(header_value: str | None, home: Path | None = None) -> bool:
    if not header_value or not header_value.startswith("Bearer "):
        return False
    supplied = header_value.removeprefix("Bearer ").strip()
    expected = configured_token(home)
    if not expected:
        return False
    return secrets.compare_digest(supplied, expected)
