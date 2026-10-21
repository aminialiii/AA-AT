---
name: metatrader-mcp
description: Use the connected MetaEditor, terminal, and market data MCP servers for MetaTrader workflows.
---

# MetaTrader MCP connections

Use the MCP tools exposed by the `metaeditor`, `terminal`, and `marketdata` servers when they are connected. Inspect each server's available tools and input schemas before calling them; don't assume a tool name or parameter based only on the server label.

The MetaEditor and terminal endpoints use loopback addresses. They require a Codex runtime on the same machine as those services. The market data endpoint is remote.

Authentication credentials are intentionally not stored in this plugin package. If Codex prompts for server authentication, enter credentials through its supported connection flow. If no such flow appears, configure the MCP servers in the local Codex configuration with environment-backed credentials and keep secret values out of project files and plugin archives.

Treat terminal or editor actions that change files, execute code, or affect a trading account as consequential. Confirm the intended target and requested action before making a change. Present market information with its source and timestamp when available, and do not present it as guaranteed financial advice.
