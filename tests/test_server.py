from pathlib import Path
import socket
import threading
import time

import anyio
import httpx
import uvicorn
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from starlette.testclient import TestClient

from flowstate_runtime.auth import ensure_token
from flowstate_runtime.server import create_app
from flowstate_runtime.store import add_stack_layer, create_object, create_stack


def test_server_requires_bearer_token(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("FLOWSTATE_HOME", str(tmp_path))
    token = ensure_token()
    app = create_app("project-alpha")

    with TestClient(app) as client:
        unauthorized = client.get("/mcp/")
        authorized = client.get("/mcp/", headers={"Authorization": f"Bearer {token}"})

    assert unauthorized.status_code == 401
    assert authorized.status_code != 401


def test_mcp_runtime_tools_are_registered(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("FLOWSTATE_HOME", str(tmp_path))
    create_object("python-base", "Python Base", home=tmp_path)
    create_stack("project-alpha", "Project Alpha", home=tmp_path)
    add_stack_layer("project-alpha", "python-base", home=tmp_path)

    from flowstate_runtime.server import create_mcp

    mcp = create_mcp("project-alpha")

    assert mcp.name == "FlowState Runtime"


def test_mcp_streamable_http_client_can_fetch_runtime(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("FLOWSTATE_HOME", str(tmp_path))
    token = ensure_token()
    create_object("python-base", "Python Base", home=tmp_path)
    create_stack("project-alpha", "Project Alpha", home=tmp_path)
    add_stack_layer("project-alpha", "python-base", home=tmp_path)

    port = _unused_port()
    server = uvicorn.Server(
        uvicorn.Config(
            create_app("project-alpha"),
            host="127.0.0.1",
            port=port,
            log_level="critical",
        )
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        _wait_for_server(server)
        payload = anyio.run(_fetch_runtime, f"http://127.0.0.1:{port}/mcp/", token)
    finally:
        server.should_exit = True
        thread.join(timeout=5)

    assert payload["runtime"] == "flow://project-alpha"
    assert payload["manifest"]["recommended_tools"][0] == "get_active_runtime_context"
    assert payload["layers"][0]["id"] == "python-base"


def _unused_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_server(server: uvicorn.Server) -> None:
    deadline = time.time() + 5
    while not server.started and time.time() < deadline:
        time.sleep(0.01)
    assert server.started


async def _fetch_runtime(endpoint: str, token: str) -> dict[str, object]:
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(headers=headers) as http_client:
        async with streamable_http_client(endpoint, http_client=http_client) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                assert {tool.name for tool in tools.tools} >= {"get_active_runtime_context", "get_runtime_manifest"}
                result = await session.call_tool("get_active_runtime_context")
                content = result.content[0]
                import json

                return json.loads(content.text)
