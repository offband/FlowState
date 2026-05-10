# FlowState Project Bootstrap Example

This repository intentionally carries only lightweight runtime attachment metadata:

```text
.flow/context.toml
.flow/codex-runtime.md
```

The operational context lives in FlowState Runtime and is served through the configured MCP endpoint. Agents should read the bootstrap file, connect to the endpoint, and retrieve the active Runtime Stack instead of relying on a large repo-local context document.
