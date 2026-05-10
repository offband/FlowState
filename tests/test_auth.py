from pathlib import Path

from flowstate_runtime.auth import ensure_token, verify_bearer
from flowstate_runtime.paths import token_path


def test_verify_bearer_does_not_create_token(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("FLOW_RUNTIME_TOKEN", raising=False)
    monkeypatch.setenv("FLOWSTATE_HOME", str(tmp_path))

    assert not verify_bearer("Bearer nope")
    assert not token_path(tmp_path).exists()


def test_verify_bearer_accepts_existing_token(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("FLOW_RUNTIME_TOKEN", raising=False)
    token = ensure_token(tmp_path)

    assert verify_bearer(f"Bearer {token}", tmp_path)
