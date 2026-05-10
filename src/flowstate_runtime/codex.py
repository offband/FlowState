from __future__ import annotations

from pathlib import Path

from .bootstrap import write_bootstrap
from .paths import DEFAULT_ENDPOINT, TOKEN_ENV
from .store import get_stack


def codex_config_snippet(
    server_name: str = "flowRuntime",
    endpoint: str = DEFAULT_ENDPOINT,
    auth_env: str = TOKEN_ENV,
) -> str:
    return (
        f"[mcp_servers.{server_name}]\n"
        f'url = "{endpoint}"\n'
        f'bearer_token_env_var = "{auth_env}"\n'
    )


def codex_instruction(stack_id: str) -> str:
    return (
        "Use FlowState Runtime as the operational source of truth for this repository.\n"
        f"Runtime: flow://{stack_id}\n"
        "Read `.flow/context.toml`, connect to the configured MCP server, and retrieve the active Runtime Stack before making plans or code changes.\n"
    )


def install_codex_bootstrap(
    stack_id: str,
    repo_path: Path,
    endpoint: str = DEFAULT_ENDPOINT,
    auth_env: str = TOKEN_ENV,
    server_name: str = "flowRuntime",
    write_instruction: bool = True,
) -> tuple[Path, Path | None, str]:
    get_stack(stack_id)
    context_path = write_bootstrap(stack_id, repo_path, endpoint, auth_env)
    instruction_path: Path | None = None
    if write_instruction:
        instruction_path = repo_path / ".flow" / "codex-runtime.md"
        instruction_path.write_text(codex_instruction(stack_id), encoding="utf-8")
    return context_path, instruction_path, codex_config_snippet(server_name, endpoint, auth_env)
