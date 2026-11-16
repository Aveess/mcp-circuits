#!/usr/bin/env python3
"""Check that the MCP server works over stdio, the way a real client uses it.

This launches ``python -m src.main`` through the MCP client SDK, performs the
handshake, lists the registered tools and calls one harmless tool
(``tinkercad_auth_status``). It exercises the protocol layer, not the service
layer the unit tests mock.

    python examples/check_mcp_stdio.py [repo_path]

Exit code is 0 only if the handshake returns tools and the call succeeds.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

REPO = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]


async def main() -> int:
    params = StdioServerParameters(
        command=str(REPO / ".venv" / "bin" / "python"),
        args=["-m", "src.main"],
        cwd=str(REPO),
        env={"PYTHONUNBUFFERED": "1"},
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            info = await session.initialize()
            print(f"handshake: {info.server_info.name} {info.server_info.version}")

            tools = await session.list_tools()
            names = sorted(tool.name for tool in tools.tools)
            print(f"tools: {len(names)}")
            if not names:
                print("FAIL: the server registered no tools")
                return 1

            result = await session.call_tool("tinkercad_auth_status", {})
            text = "".join(
                getattr(block, "text", "") for block in result.content
            ).strip()
            print(f"call_tool error: {getattr(result, 'isError', None)}")
            if text:
                try:
                    data = json.loads(text)
                except json.JSONDecodeError:
                    print(text[:400])
                else:
                    print(f"authenticated: {data.get('authenticated')} ({data.get('message')})")
            if getattr(result, "isError", False):
                print("FAIL: the tool returned an error")
                return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
