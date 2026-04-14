#!/usr/bin/env python3

import sys, os
sys.path.insert(0, os.path.expanduser('~/clawd/meok-labs-engine/shared'))
from auth_middleware import check_access

import json, uuid
from mcp.server.fastmcp import FastMCP
mcp = FastMCP("agent-delegation-mcp")
_TASKS: dict = {}
@mcp.tool(name="delegate_task")
async def delegate_task(agent_id: str, task_description: str, priority: str = "medium", api_key: str = "") -> str:
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://meok.ai/pricing"}

    tid = str(uuid.uuid4())[:12]
    _TASKS[tid] = {"agent": agent_id, "task": task_description, "priority": priority, "status": "pending"}
    return {"task_id": tid, "agent": agent_id, "status": "delegated"}
@mcp.tool(name="task_status")
async def task_status(task_id: str, api_key: str = "") -> str:
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://meok.ai/pricing"}

    t = _TASKS.get(task_id)
    return t or {"error": "Task not found"}
@mcp.tool(name="list_pending_tasks")
async def list_pending_tasks(agent_id: str, api_key: str = "") -> str:
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://meok.ai/pricing"}

    return {"tasks": [t for t in _TASKS.values() if t["agent"] == agent_id and t["status"] == "pending"]}
    return {"tasks": [t for t in _TASKS.values() if t["agent"] == agent_id and t["status"] == "pending"]}
if __name__ == "__main__":
    mcp.run()
