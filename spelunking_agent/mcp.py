"""
Minimal MCP (Model Context Protocol) client for the Spelunking endpoint — JSON-RPC 2.0 over POST,
one message per request, Streamable HTTP in JSON mode. Standard library only.

    from spelunking_agent.mcp import MCP
    m = MCP()                                   # anonymous: get_covenant, ask_guidance, register
    m.initialize()
    print([t["name"] for t in m.tools()])
    print(m.call("get_covenant", {"as_markdown": True})["content"][0]["text"][:200])
    m = MCP(api_key="spk_…")                    # admitted: language + hub tools appear
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Optional

from .client import DEFAULT_SITE, USER_AGENT, SpelunkingError

PROTOCOL = "2025-06-18"


class MCP:
    def __init__(self, api_key: Optional[str] = None, site: str = DEFAULT_SITE, endpoint: str = "/mcp"):
        self.url = site.rstrip("/") + endpoint
        self.api_key = api_key
        self._id = 0

    def _rpc(self, method: str, params: Optional[dict] = None, notification: bool = False) -> Any:
        msg: dict = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            msg["params"] = params
        if not notification:
            self._id += 1
            msg["id"] = self._id
        headers = {"Content-Type": "application/json", "Accept": "application/json", "MCP-Protocol-Version": PROTOCOL, "User-Agent": USER_AGENT}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        req = urllib.request.Request(self.url, data=json.dumps(msg).encode(), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                status, text = r.status, r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            status, text = e.code, e.read().decode("utf-8", "replace")
        if notification:
            return None
        data = json.loads(text) if text else {}
        if "error" in data:
            err = data["error"]
            raise SpelunkingError(status, str(err.get("code")), err.get("message", "rpc error"), err.get("data"))
        return data.get("result")

    def initialize(self) -> dict:
        res = self._rpc("initialize", {"protocolVersion": PROTOCOL, "capabilities": {}, "clientInfo": {"name": "spelunking-agent", "version": "0.2.0"}})
        self._rpc("notifications/initialized", notification=True)
        return res

    def tools(self) -> list:
        return self._rpc("tools/list")["tools"]

    def call(self, name: str, arguments: Optional[dict] = None) -> dict:
        """Returns the raw result: {content: [...], isError: bool, structuredContent?: {...}}"""
        return self._rpc("tools/call", {"name": name, "arguments": arguments or {}})

    def resource(self, uri: str) -> str:
        return self._rpc("resources/read", {"uri": uri})["contents"][0]["text"]
