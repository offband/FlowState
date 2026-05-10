# Connect Codex To FlowState Runtime

FlowState V1 exposes runtime context through a local authenticated MCP-compatible Streamable HTTP endpoint.

## 1. Install And Initialize

```bash
pipx install git+https://github.com/<owner>/flowstate.git
flow init
flow examples install
flow stack manifest ai-builder
```

For local development from this repo:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
flow init
flow examples install
```

## 2. Export The Runtime Token

```bash
export FLOW_RUNTIME_TOKEN="$(flow auth token)"
```

## 3. Start The Runtime Server

```bash
flow serve ai-builder
```

The MCP endpoint is:

```text
http://localhost:7777/mcp
```

## 4. Configure Codex MCP

Use Streamable HTTP:

```text
Name: FlowState Runtime
URL: http://localhost:7777/mcp
Bearer token env var: FLOW_RUNTIME_TOKEN
```

## 5. Attach A Project

From any project repo:

```bash
flow codex install ai-builder --path .
```

This writes:

```text
.flow/context.toml
.flow/codex-runtime.md
```

Example:

```toml
runtime = "flow://ai-builder"
endpoint = "http://localhost:7777/mcp"
auth_env = "FLOW_RUNTIME_TOKEN"
source_of_truth = "FlowState Runtime Endpoint"
```

This tiny file tells humans and agents that operational context lives in FlowState Runtime rather than in a large repo-local context file.

Inspect the attachment:

```bash
flow bootstrap inspect --path .
flow drift --path .
```

## Runtime Retrieval Tools

The MCP server exposes:

- `list_runtime_stacks`
- `get_active_runtime_context`
- `get_runtime_stack`
- `get_runtime_manifest`
- `get_runtime_stack_markdown`
- `get_runtime_stack_provenance`

Runtime responses preserve object boundaries, source paths, metadata, and ordered provenance.

The MCP server also exposes prompts:

- `use_runtime_context`
- `review_with_runtime`
- `plan_with_runtime`
