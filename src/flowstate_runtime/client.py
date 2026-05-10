from __future__ import annotations

import json
import os
from typing import Any

import anyio
import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def resolve_runtime_async(
    endpoint: str,
    stack_id: str | None,
    auth_env: str,
    markdown: bool = False,
) -> Any:
    token = os.environ.get(auth_env)
    if not token:
        raise RuntimeError(f"Missing runtime auth environment variable: {auth_env}")
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(headers=headers) as http_client:
        async with streamable_http_client(endpoint, http_client=http_client) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tool_name = "get_runtime_stack_markdown" if markdown else "get_runtime_stack"
                result = await session.call_tool(tool_name, {"stack_id": stack_id})
                content = result.content[0]
                text = getattr(content, "text", content)
                if markdown or not isinstance(text, str):
                    return text
                return json.loads(text)


def resolve_runtime(endpoint: str, stack_id: str | None, auth_env: str, markdown: bool = False) -> Any:
    return anyio.run(resolve_runtime_async, endpoint, stack_id, auth_env, markdown)
