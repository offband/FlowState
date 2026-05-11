# FlowState Project Bootstrap Example

This repository intentionally carries only lightweight runtime attachment metadata:

```text
.flow/context.toml
.flow/codex-runtime.md
```

The operational context lives in FlowState Runtime and is served through the configured MCP endpoint. Agents should read the bootstrap file, connect to the endpoint, and retrieve the active Runtime Stack instead of relying on a large repo-local context document.

For Codex Desktop on macOS, set persistent GUI auth before connecting:

```bash
launchctl setenv FLOW_RUNTIME_TOKEN "$(flow auth token)"
```

`launchctl` is macOS-specific. Use temporary shell-local auth only for commands launched from the current terminal:

```bash
export FLOW_RUNTIME_TOKEN="$(flow auth token)"
```

Cleanup:

```bash
launchctl unsetenv FLOW_RUNTIME_TOKEN
```

Troubleshooting:

- The MCP URL must end with `/mcp/`.
- Codex may require a full restart after auth changes.
- The FlowState runtime server must be actively serving.
- A missing `FLOW_RUNTIME_TOKEN` prevents runtime resolution.
