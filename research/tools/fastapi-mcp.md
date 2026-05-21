---
title: fastapi-mcp
aliases: [fastapi_mcp]
tags: [verify-kit, tools, mcp, backend-addon, opt-in]
created: 2026-05-18
status: OPT-IN
layer: Backend Add-on
phase_introduced: Phase 4
---

# 🔌 fastapi-mcp

> [!abstract] One-line summary
> Three-line mount that turns every FastAPI route into an MCP tool — callable from `claude mcp` or any MCP client.

## What it does

`fastapi-mcp` introspects a FastAPI app's routes and exposes each one as a tool in an MCP (Model Context Protocol) server. The MCP client (Claude Code, Cursor, OpenCode, etc.) gets a typed tool catalog with annotations (`readOnlyHint`, `destructiveHint`, `idempotentHint`). Same route serves both human HTTP clients and AI agents — no duplicate endpoint definitions.

## Why we picked it (as opt-in)

When the consumer enables `has_backend=true` AND opts into `has_fastapi_mcp=true`, the backend's HTTP API becomes an agent toolkit "for free":

- ✅ One source of truth (the FastAPI route)
- ✅ MCP annotations let agents reason about side effects
- ✅ Composes with the universal MCP server from Phase 3 (verify-kit's own MCP tools)

| Alternative | Why secondary |
|---|---|
| Hand-write MCP tool definitions | Reinvent the route's input/output models; drift risk |
| `langchain` tool-calling | Provider-locked; not MCP-standard |

Opt-in (not default) because not every backend project wants to expose itself to agents. See [[agent-reports/wave-4-mcp-agent-integration]].

## Usage in verify-kit

When `has_backend=true` AND `has_fastapi_mcp=true`, Copier scaffolds:

```python
# app/main.py
from fastapi import FastAPI
from fastapi_mcp import FastApiMCP

app = FastAPI()

# ... routes ...

# Three lines that turn the API into an MCP server:
mcp = FastApiMCP(app)
mcp.mount()  # mounts MCP transport at /mcp
```

The generated `claude mcp add` snippet (in CLAUDE.md or README) connects Claude Code to the running backend's MCP server.

## Install

```python
# In generated project deps when has_backend=true AND has_fastapi_mcp=true
"fastapi-mcp>=0.1",
```

## Gotchas

- **Route annotations matter** — without `readOnlyHint=True` on `GET` routes, agents may treat them as destructive. Annotate explicitly.
- **Path parameters become tool args** — `@app.get("/users/{user_id}")` becomes a tool taking `user_id: str`. Type hints determine the MCP schema.
- **Auth on MCP transport** — by default, the MCP mount inherits FastAPI middleware. Token-based auth for the MCP transport is configurable; document the chosen pattern in the generated README.
- **Annotations differ from CLI tool annotations** — Phase 3's universal MCP tools use a similar but not identical annotation set; check that the catalogs don't collide.

## Key docs

- Repo: <https://github.com/tadata-org/fastapi_mcp>
- MCP spec: <https://modelcontextprotocol.io/>
- Annotations: <https://modelcontextprotocol.io/specification/tools#tool-annotations>

## Related notes

- [[00-stack-decisions#Backend Add-on]] — opt-in slot
- [[agent-reports/wave-4-mcp-agent-integration]] — wave context
- [[agent-reports/wave-4-fastapi-ecosystem]] — broader Backend add-on stack
