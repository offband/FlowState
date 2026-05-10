from __future__ import annotations

from pathlib import Path
from typing import Any

from .bootstrap import read_bootstrap
from .client import resolve_runtime
from .compose import compose_stack
from .paths import TOKEN_ENV
from .store import RuntimeStoreError


def inspect_drift(repo_path: Path, remote: bool = False) -> dict[str, Any]:
    bootstrap = read_bootstrap(repo_path)
    stack_id = bootstrap.get("stack_id")
    checks: list[dict[str, Any]] = []

    def add_check(name: str, ok: bool, detail: str) -> None:
        checks.append({"name": name, "ok": ok, "detail": detail})

    add_check("bootstrap", True, str(repo_path / ".flow" / "context.toml"))
    add_check("runtime", isinstance(stack_id, str) and bool(stack_id), str(bootstrap.get("runtime", "")))

    auth_env = bootstrap.get("auth_env") or TOKEN_ENV
    auth_available = bool(bootstrap.get("auth_available"))
    add_check(
        "auth_env",
        auth_available or not remote,
        f"{auth_env}{' set' if auth_available else ' not set'}",
    )

    local_manifest: dict[str, Any] | None = None
    try:
        local_manifest = compose_stack(str(stack_id)).manifest()
        add_check("local_stack", True, local_manifest["digest"])
    except (RuntimeStoreError, TypeError) as exc:
        add_check("local_stack", False, str(exc))

    remote_manifest: dict[str, Any] | None = None
    if remote:
        try:
            remote_payload = resolve_runtime(str(bootstrap["endpoint"]), str(stack_id), str(auth_env), markdown=False)
            if isinstance(remote_payload, dict):
                remote_manifest = remote_payload.get("manifest") or {}
            add_check("remote_endpoint", bool(remote_manifest), str((remote_manifest or {}).get("digest", "")))
        except Exception as exc:  # pragma: no cover - exact client errors vary by transport
            add_check("remote_endpoint", False, str(exc))

    if local_manifest and remote_manifest:
        add_check(
            "digest_match",
            local_manifest.get("digest") == remote_manifest.get("digest"),
            f"local={local_manifest.get('digest')} remote={remote_manifest.get('digest')}",
        )

    return {
        "status": "ok" if all(check["ok"] for check in checks) else "drift",
        "bootstrap": bootstrap,
        "local_manifest": local_manifest,
        "remote_manifest": remote_manifest,
        "checks": checks,
    }
