from __future__ import annotations

import os
from pathlib import Path


RUNTIME_HOME_ENV = "FLOWSTATE_HOME"
TOKEN_ENV = "FLOW_RUNTIME_TOKEN"
DEFAULT_ENDPOINT = "http://localhost:7777/mcp/"


def runtime_home() -> Path:
    configured = os.environ.get(RUNTIME_HOME_ENV)
    if configured:
        return Path(configured).expanduser().resolve()
    return Path.home() / ".flow"


def objects_dir(home: Path | None = None) -> Path:
    return (home or runtime_home()) / "objects"


def stacks_dir(home: Path | None = None) -> Path:
    return (home or runtime_home()) / "stacks"


def keys_dir(home: Path | None = None) -> Path:
    return (home or runtime_home()) / "keys"


def exports_dir(home: Path | None = None) -> Path:
    return (home or runtime_home()) / "exports"


def config_path(home: Path | None = None) -> Path:
    return (home or runtime_home()) / "config.toml"


def token_path(home: Path | None = None) -> Path:
    return keys_dir(home) / "runtime.token"
