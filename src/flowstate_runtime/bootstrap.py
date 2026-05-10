from __future__ import annotations

from pathlib import Path
import os
import tomllib
from typing import Any

from .paths import DEFAULT_ENDPOINT, TOKEN_ENV
from .store import RuntimeStoreError, validate_id


def bootstrap_text(stack_id: str, endpoint: str = DEFAULT_ENDPOINT, auth_env: str = TOKEN_ENV) -> str:
    validate_id(stack_id)
    return (
        f'runtime = "flow://{stack_id}"\n'
        f'endpoint = "{endpoint}"\n'
        f'auth_env = "{auth_env}"\n'
        'source_of_truth = "FlowState Runtime Endpoint"\n'
    )


def write_bootstrap(stack_id: str, repo_path: Path, endpoint: str = DEFAULT_ENDPOINT, auth_env: str = TOKEN_ENV) -> Path:
    flow_dir = repo_path / ".flow"
    flow_dir.mkdir(parents=True, exist_ok=True)
    target = flow_dir / "context.toml"
    target.write_text(bootstrap_text(stack_id, endpoint, auth_env), encoding="utf-8")
    return target


def bootstrap_path(repo_path: Path) -> Path:
    return repo_path / ".flow" / "context.toml"


def read_bootstrap(repo_path: Path) -> dict[str, Any]:
    path = bootstrap_path(repo_path)
    if not path.exists():
        raise RuntimeStoreError(f"Bootstrap file not found: {path}")
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise RuntimeStoreError(f"Invalid bootstrap TOML: {path}") from exc
    runtime = data.get("runtime", "")
    if not isinstance(runtime, str) or not runtime.startswith("flow://"):
        raise RuntimeStoreError(f"Bootstrap runtime must use flow:// scheme: {path}")
    stack_id = runtime.removeprefix("flow://")
    validate_id(stack_id)
    data["stack_id"] = stack_id
    endpoint = data.get("endpoint")
    if not isinstance(endpoint, str) or not endpoint:
        raise RuntimeStoreError(f"Bootstrap endpoint is required: {path}")
    auth_env = data.get("auth_env", TOKEN_ENV)
    if not isinstance(auth_env, str) or not auth_env:
        raise RuntimeStoreError(f"Bootstrap auth_env must be a non-empty string: {path}")
    data["auth_available"] = bool(os.environ.get(auth_env))
    return data
