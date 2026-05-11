from __future__ import annotations

import contextlib
import json
from typing import Callable

import uvicorn
from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount

from .auth import ensure_token, verify_bearer
from .compose import compose_stack
from .store import RuntimeStoreError, list_stacks


class BearerAuthMiddleware(BaseHTTPMiddleware):
    allowed_origins = {
        "http://127.0.0.1",
        "http://[::1]",
        "null",
    }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.method == "OPTIONS":
            return await call_next(request)
        origin = request.headers.get("origin")
        if origin and not any(origin.startswith(allowed) for allowed in self.allowed_origins):
            return JSONResponse({"error": "forbidden origin"}, status_code=403)
        if not verify_bearer(request.headers.get("authorization")):
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        return await call_next(request)


def create_mcp(default_stack: str | None = None) -> FastMCP:
    mcp = FastMCP("FlowState Runtime", stateless_http=True, json_response=True, streamable_http_path="/mcp/")

    @mcp.tool()
    def list_runtime_stacks() -> list[dict[str, object]]:
        """List available FlowState Runtime Stacks."""
        return [
            {
                "id": stack.id,
                "title": stack.title,
                "layers": stack.layers,
                "path": str(stack.path),
            }
            for stack in list_stacks()
        ]

    @mcp.tool()
    def get_runtime_stack(stack_id: str | None = None) -> dict[str, object]:
        """Retrieve an assembled Runtime Stack with object boundaries and provenance."""
        resolved_stack = stack_id or default_stack
        if not resolved_stack:
            raise RuntimeStoreError("No stack_id supplied and no default stack configured")
        return compose_stack(resolved_stack).to_dict()

    @mcp.tool()
    def get_active_runtime_context() -> dict[str, object]:
        """Retrieve the default active Runtime Stack for this server."""
        if not default_stack:
            raise RuntimeStoreError("No default stack configured")
        return compose_stack(default_stack).to_dict()

    @mcp.tool()
    def get_runtime_manifest(stack_id: str | None = None) -> dict[str, object]:
        """Retrieve Runtime Stack manifest, digest, tool guidance, and layer summary."""
        resolved_stack = stack_id or default_stack
        if not resolved_stack:
            raise RuntimeStoreError("No stack_id supplied and no default stack configured")
        return compose_stack(resolved_stack).manifest()

    @mcp.tool()
    def get_runtime_stack_markdown(stack_id: str | None = None) -> str:
        """Retrieve an assembled Runtime Stack as Markdown while preserving layer provenance."""
        resolved_stack = stack_id or default_stack
        if not resolved_stack:
            raise RuntimeStoreError("No stack_id supplied and no default stack configured")
        return compose_stack(resolved_stack).to_markdown()

    @mcp.tool()
    def get_runtime_stack_provenance(stack_id: str | None = None) -> dict[str, object]:
        """Retrieve Runtime Stack layer provenance without full object content."""
        resolved_stack = stack_id or default_stack
        if not resolved_stack:
            raise RuntimeStoreError("No stack_id supplied and no default stack configured")
        composed = compose_stack(resolved_stack)
        payload = composed.to_dict()
        return {
            "runtime": payload["runtime"],
            "stack": payload["stack"],
            "layers": [
                {
                    "index": layer["index"],
                    "id": layer["id"],
                    "title": layer["title"],
                    "version": layer["version"],
                    "path": layer["path"],
                    "metadata": layer["metadata"],
                }
                for layer in payload["layers"]
            ],
        }

    @mcp.resource("flow://stacks")
    def stacks_resource() -> str:
        """JSON list of available Runtime Stacks."""
        return json.dumps(
            [
                {
                    "id": stack.id,
                    "title": stack.title,
                    "layers": stack.layers,
                    "path": str(stack.path),
                }
                for stack in list_stacks()
            ],
            indent=2,
        )

    @mcp.resource("flow://stack/{stack_id}")
    def stack_resource(stack_id: str) -> str:
        """JSON assembled Runtime Stack by ID."""
        return json.dumps(compose_stack(stack_id).to_dict(), indent=2)

    @mcp.prompt()
    def use_runtime_context(stack_id: str | None = None) -> str:
        """Create an instruction to use a Runtime Stack as source of truth."""
        resolved_stack = stack_id or default_stack
        if not resolved_stack:
            raise RuntimeStoreError("No stack_id supplied and no default stack configured")
        manifest = compose_stack(resolved_stack).manifest()
        return (
            "Use FlowState Runtime as the operational source of truth before planning or editing.\n"
            f"Runtime: {manifest['runtime']}\n"
            f"Digest: {manifest['digest']}\n"
            "Retrieve the full runtime context and follow its layer ordering and provenance."
        )

    @mcp.prompt()
    def review_with_runtime(stack_id: str | None = None) -> str:
        """Create a review instruction grounded in FlowState Runtime context."""
        resolved_stack = stack_id or default_stack
        if not resolved_stack:
            raise RuntimeStoreError("No stack_id supplied and no default stack configured")
        return (
            f"Retrieve flow://{resolved_stack} from FlowState Runtime, then review the current change against "
            "the product, planning, PRD, review, deployment, and issue-resolution layers."
        )

    @mcp.prompt()
    def plan_with_runtime(stack_id: str | None = None) -> str:
        """Create a planning instruction grounded in FlowState Runtime context."""
        resolved_stack = stack_id or default_stack
        if not resolved_stack:
            raise RuntimeStoreError("No stack_id supplied and no default stack configured")
        return (
            f"Retrieve flow://{resolved_stack} from FlowState Runtime, then draft an implementation plan that "
            "preserves runtime invariants and cites relevant runtime layers."
        )

    return mcp


def create_app(default_stack: str | None = None) -> Starlette:
    mcp = create_mcp(default_stack)

    @contextlib.asynccontextmanager
    async def lifespan(app: Starlette):
        async with mcp.session_manager.run():
            yield

    app = Starlette(routes=[Mount("/", app=mcp.streamable_http_app())], lifespan=lifespan)
    app.add_middleware(BearerAuthMiddleware)
    return app


def run_server(host: str = "127.0.0.1", port: int = 7777, default_stack: str | None = None) -> None:
    ensure_token()
    uvicorn.run(create_app(default_stack), host=host, port=port)
