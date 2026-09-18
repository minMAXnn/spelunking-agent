"""Use the MCP endpoint directly (JSON-RPC over POST). Any MCP client works; this is the no-dependency one."""
import os
from spelunking_agent.mcp import MCP

m = MCP(api_key=os.environ.get("SPELUNKING_API_KEY"))
print(m.initialize()["instructions"])
print([t["name"] for t in m.tools()])
print(m.call("ask_guidance", {"text": "hello"})["structuredContent"]["tag"])
print(m.resource("spelunking://agents")[:300])
