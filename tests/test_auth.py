from pathlib import Path
from stat import S_IMODE

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


def test_existing_token_permissions_are_repaired(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("FLOW_RUNTIME_TOKEN", raising=False)
    path = token_path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text("existing-token\n", encoding="utf-8")
    path.chmod(0o644)

    assert ensure_token(tmp_path) == "existing-token"
    assert S_IMODE(path.stat().st_mode) == 0o600


def test_blank_token_file_is_regenerated(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("FLOW_RUNTIME_TOKEN", raising=False)
    path = token_path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text("\n", encoding="utf-8")
    path.chmod(0o644)

    token = ensure_token(tmp_path)

    assert token
    assert token == path.read_text(encoding="utf-8").strip()
    assert S_IMODE(path.stat().st_mode) == 0o600
