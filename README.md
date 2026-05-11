# FlowState

Local-first runtime context layer for AI-assisted systems.

FlowState turns scattered agent instructions into addressable runtime infrastructure.

Think: package manager for agent context.

```text
Runtime Objects -> Runtime Stack -> Runtime Endpoint -> Codex / Cursor / Claude
```

## Quick Demo

```bash
pipx install git+https://github.com/offband/flowstate.git

flow init
flow examples install
launchctl setenv FLOW_RUNTIME_TOKEN "$(flow auth token)"
flow serve ai-builder
```

For Codex Desktop on macOS, prefer `launchctl setenv` because GUI apps do not reliably inherit shell environment variables. `launchctl` is macOS-specific and persists the token for GUI apps launched after the value is set.

For temporary shell-local auth in the current terminal only:

```bash
export FLOW_RUNTIME_TOKEN="$(flow auth token)"
```

To clean up the macOS GUI token:

```bash
launchctl unsetenv FLOW_RUNTIME_TOKEN
```

Configure Codex as a Streamable HTTP MCP server:

```toml
[mcp_servers.flowRuntime]
url = "http://127.0.0.1:7777/mcp/"
bearer_token_env_var = "FLOW_RUNTIME_TOKEN"
```

Attach any project to the runtime:

```bash
flow codex install ai-builder --path /path/to/project
```

The project now contains:

```text
.flow/context.toml
.flow/codex-runtime.md
```

Agents read the attachment, connect to the MCP endpoint, and retrieve the active Runtime Stack.

Troubleshooting:

- The MCP URL must end with `/mcp/`.
- Codex may require a full restart after auth changes.
- `flow serve ai-builder` must be actively serving while Codex resolves runtime context.
- A missing `FLOW_RUNTIME_TOKEN` prevents runtime resolution.

## Why

Agent context is fragmented:

- `AGENTS.md`
- Cursor rules
- Claude memory
- Copilot instructions
- giant pasted prompts
- repo drift

FlowState centralizes reusable operational context into composable runtime infrastructure.

## Primitives

**Runtime Objects**  
Markdown/YAML files containing standards, review rules, deployment rules, and project conventions.

**Runtime Stacks**  
Ordered compositions of Runtime Objects. Stacks preserve boundaries, provenance, inheritance, and layer order.

**Runtime Manifest**  
Digest-backed identity for a composed stack: runtime URI, layer list, source stacks, retrieval tools.

**Runtime Endpoints**  
Authenticated MCP-compatible HTTP endpoints that expose Runtime Stacks to tools.

**Runtime Attachments**  
Tiny project-local pointers, usually `.flow/context.toml`.

## Inspect And Export

Live retrieval through MCP:

```bash
flow stack manifest ai-builder
flow stack inspect ai-builder
flow resolve --path /path/to/project
```

Durable compatibility through export:

```bash
flow stack export ai-builder --format markdown
flow stack export ai-builder --format json
```

MCP is the live path. Export is the fallback.

## Security / Non-Execution

FlowState does not:

- execute code
- orchestrate agents
- mutate repositories
- call model providers
- generate context with AI

FlowState only:

- stores
- composes
- exposes

operational context.

## Local Files

```text
~/.flow/
  objects/
  stacks/
  keys/
  exports/
```

Runtime Objects are plain Markdown. Runtime Stacks are YAML. Project attachments are TOML.
