#!/usr/bin/env python3
"""Agent Delegation MCP Server - Create, delegate, track, and complete tasks across agents."""

import sys, os
sys.path.insert(0, os.path.expanduser('~/clawd/meok-labs-engine/shared'))
from auth_middleware import check_access

import json, time, uuid
from collections import defaultdict
from mcp.server.fastmcp import FastMCP

# Rate limiting
_rate_limits: dict = defaultdict(list)
RATE_WINDOW = 60
MAX_REQUESTS = 30

def _check_rate(key: str) -> bool:
    now = time.time()
    _rate_limits[key] = [t for t in _rate_limits[key] if now - t < RATE_WINDOW]
    if len(_rate_limits[key]) >= MAX_REQUESTS:
        return False
    _rate_limits[key].append(now)
    return True

# In-memory stores
_TASKS: dict = {}
_AGENTS: dict = {}

# Pre-registered agent pool
DEFAULT_AGENTS = {
    "agent-research": {
        "agent_id": "agent-research",
        "name": "Research Agent",
        "capabilities": ["web_search", "document_analysis", "summarization", "fact_checking"],
        "status": "available",
        "max_concurrent": 3,
        "current_tasks": 0,
        "completed_total": 0,
        "avg_completion_seconds": 120,
        "registered_at": "2026-01-01T00:00:00Z",
    },
    "agent-code": {
        "agent_id": "agent-code",
        "name": "Code Agent",
        "capabilities": ["code_generation", "code_review", "testing", "debugging", "refactoring"],
        "status": "available",
        "max_concurrent": 2,
        "current_tasks": 0,
        "completed_total": 0,
        "avg_completion_seconds": 180,
        "registered_at": "2026-01-01T00:00:00Z",
    },
    "agent-writer": {
        "agent_id": "agent-writer",
        "name": "Writing Agent",
        "capabilities": ["content_writing", "editing", "proofreading", "translation", "tone_adjustment"],
        "status": "available",
        "max_concurrent": 5,
        "current_tasks": 0,
        "completed_total": 0,
        "avg_completion_seconds": 90,
        "registered_at": "2026-01-01T00:00:00Z",
    },
    "agent-data": {
        "agent_id": "agent-data",
        "name": "Data Agent",
        "capabilities": ["data_analysis", "visualization", "etl", "sql_query", "statistics"],
        "status": "available",
        "max_concurrent": 2,
        "current_tasks": 0,
        "completed_total": 0,
        "avg_completion_seconds": 240,
        "registered_at": "2026-01-01T00:00:00Z",
    },
    "agent-ops": {
        "agent_id": "agent-ops",
        "name": "Operations Agent",
        "capabilities": ["deployment", "monitoring", "alerting", "scaling", "log_analysis"],
        "status": "available",
        "max_concurrent": 3,
        "current_tasks": 0,
        "completed_total": 0,
        "avg_completion_seconds": 60,
        "registered_at": "2026-01-01T00:00:00Z",
    },
}

# Initialize agents
_AGENTS.update(DEFAULT_AGENTS)

VALID_PRIORITIES = ["critical", "high", "medium", "low"]
VALID_STATUSES = ["pending", "assigned", "in_progress", "completed", "failed", "cancelled"]

mcp = FastMCP("agent-delegation-mcp", instructions="Create and delegate tasks to specialized agents, track progress, and manage task lifecycle. Supports priority queuing and capability-based agent matching.")


@mcp.tool()
async def create_task(title: str, description: str, priority: str = "medium", required_capabilities: str = "", timeout_seconds: int = 3600, api_key: str = "") -> str:
    """Create a new delegatable task. Required capabilities as comma-separated string."""
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return json.dumps({"error": msg, "upgrade_url": "https://meok.ai/pricing"})
    if not _check_rate(api_key or "anon"):
        return json.dumps({"error": "Rate limit exceeded. Try again in 60 seconds."})

    if not title.strip():
        return json.dumps({"error": "Task title is required"})
    if not description.strip():
        return json.dumps({"error": "Task description is required"})
    if priority.lower() not in VALID_PRIORITIES:
        return json.dumps({"error": f"Priority must be one of: {VALID_PRIORITIES}"})

    task_id = f"TASK-{str(uuid.uuid4())[:8]}"
    caps = [c.strip() for c in required_capabilities.split(",") if c.strip()] if required_capabilities else []

    now = time.time()
    task = {
        "task_id": task_id,
        "title": title,
        "description": description,
        "priority": priority.lower(),
        "status": "pending",
        "required_capabilities": caps,
        "assigned_agent": None,
        "timeout_seconds": timeout_seconds,
        "created_at": now,
        "created_at_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "assigned_at": None,
        "started_at": None,
        "completed_at": None,
        "deadline": now + timeout_seconds,
        "result": None,
        "error": None,
        "history": [{"event": "created", "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}],
    }

    _TASKS[task_id] = task

    # Find compatible agents
    compatible_agents = []
    for agent in _AGENTS.values():
        if agent["status"] != "available":
            continue
        if caps and not all(c in agent["capabilities"] for c in caps):
            continue
        if agent["current_tasks"] >= agent["max_concurrent"]:
            continue
        compatible_agents.append({
            "agent_id": agent["agent_id"],
            "name": agent["name"],
            "matching_capabilities": [c for c in caps if c in agent["capabilities"]],
        })

    return json.dumps({
        "task_id": task_id,
        "status": "pending",
        "title": title,
        "priority": priority.lower(),
        "required_capabilities": caps,
        "compatible_agents": compatible_agents,
        "created_at": task["created_at_iso"],
        "deadline": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(task["deadline"])),
    })


@mcp.tool()
async def delegate_task(task_id: str, agent_id: str, api_key: str = "") -> str:
    """Assign a pending task to a specific agent."""
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return json.dumps({"error": msg, "upgrade_url": "https://meok.ai/pricing"})
    if not _check_rate(api_key or "anon"):
        return json.dumps({"error": "Rate limit exceeded. Try again in 60 seconds."})

    task = _TASKS.get(task_id)
    if not task:
        return json.dumps({"error": f"Task '{task_id}' not found"})

    if task["status"] not in ["pending", "failed"]:
        return json.dumps({"error": f"Task is '{task['status']}' - only pending or failed tasks can be delegated"})

    agent = _AGENTS.get(agent_id)
    if not agent:
        return json.dumps({"error": f"Agent '{agent_id}' not found. Use list_available_agents to see options."})

    if agent["status"] != "available":
        return json.dumps({"error": f"Agent '{agent_id}' is currently '{agent['status']}'"})

    if agent["current_tasks"] >= agent["max_concurrent"]:
        return json.dumps({"error": f"Agent '{agent_id}' at capacity ({agent['current_tasks']}/{agent['max_concurrent']} tasks)"})

    # Check capability match
    missing_caps = [c for c in task["required_capabilities"] if c not in agent["capabilities"]]
    if missing_caps:
        return json.dumps({
            "error": "capability_mismatch",
            "message": f"Agent lacks required capabilities: {missing_caps}",
            "agent_capabilities": agent["capabilities"],
            "required": task["required_capabilities"],
        })

    # Perform delegation
    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    task["status"] = "assigned"
    task["assigned_agent"] = agent_id
    task["assigned_at"] = now_iso
    task["history"].append({"event": "delegated", "agent_id": agent_id, "timestamp": now_iso})

    agent["current_tasks"] += 1
    if agent["current_tasks"] >= agent["max_concurrent"]:
        agent["status"] = "busy"

    # Auto-transition to in_progress
    task["status"] = "in_progress"
    task["started_at"] = now_iso
    task["history"].append({"event": "started", "timestamp": now_iso})

    return json.dumps({
        "task_id": task_id,
        "status": "in_progress",
        "assigned_agent": agent_id,
        "agent_name": agent["name"],
        "delegated_at": now_iso,
        "estimated_completion_seconds": agent["avg_completion_seconds"],
        "deadline": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(task["deadline"])),
    })


@mcp.tool()
async def get_task_status(task_id: str, include_history: bool = False, api_key: str = "") -> str:
    """Check the current status and progress of a task."""
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return json.dumps({"error": msg, "upgrade_url": "https://meok.ai/pricing"})
    if not _check_rate(api_key or "anon"):
        return json.dumps({"error": "Rate limit exceeded. Try again in 60 seconds."})

    task = _TASKS.get(task_id)
    if not task:
        return json.dumps({"error": f"Task '{task_id}' not found"})

    now = time.time()
    is_overdue = task["status"] in ["pending", "assigned", "in_progress"] and now > task["deadline"]

    # Calculate elapsed time
    elapsed = None
    if task["started_at"]:
        try:
            from datetime import datetime
            started = datetime.strptime(task["started_at"], "%Y-%m-%dT%H:%M:%SZ")
            elapsed_seconds = (datetime.utcnow() - started).total_seconds()
            elapsed = round(elapsed_seconds, 0)
        except Exception:
            elapsed = None

    result = {
        "task_id": task_id,
        "title": task["title"],
        "description": task["description"],
        "priority": task["priority"],
        "status": task["status"],
        "assigned_agent": task["assigned_agent"],
        "created_at": task["created_at_iso"],
        "assigned_at": task["assigned_at"],
        "started_at": task["started_at"],
        "completed_at": task["completed_at"],
        "elapsed_seconds": elapsed,
        "is_overdue": is_overdue,
        "deadline": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(task["deadline"])),
    }

    if task["result"]:
        result["result"] = task["result"]
    if task["error"]:
        result["error"] = task["error"]
    if include_history:
        result["history"] = task["history"]

    # Agent info
    if task["assigned_agent"]:
        agent = _AGENTS.get(task["assigned_agent"])
        if agent:
            result["agent_name"] = agent["name"]

    return json.dumps(result)


@mcp.tool()
async def list_available_agents(capability_filter: str = "", api_key: str = "") -> str:
    """List all registered agents and their capabilities. Optionally filter by required capability."""
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return json.dumps({"error": msg, "upgrade_url": "https://meok.ai/pricing"})
    if not _check_rate(api_key or "anon"):
        return json.dumps({"error": "Rate limit exceeded. Try again in 60 seconds."})

    required_caps = [c.strip() for c in capability_filter.split(",") if c.strip()] if capability_filter else []

    agents_list = []
    for agent in _AGENTS.values():
        if required_caps and not all(c in agent["capabilities"] for c in required_caps):
            continue

        # Count active tasks for this agent
        active_tasks = [t for t in _TASKS.values() if t["assigned_agent"] == agent["agent_id"] and t["status"] in ["assigned", "in_progress"]]

        agents_list.append({
            "agent_id": agent["agent_id"],
            "name": agent["name"],
            "status": agent["status"],
            "capabilities": agent["capabilities"],
            "capacity": f"{agent['current_tasks']}/{agent['max_concurrent']}",
            "is_available": agent["status"] == "available" and agent["current_tasks"] < agent["max_concurrent"],
            "active_tasks": len(active_tasks),
            "completed_total": agent["completed_total"],
            "avg_completion_seconds": agent["avg_completion_seconds"],
        })

    # Sort: available first, then by name
    agents_list.sort(key=lambda a: (0 if a["is_available"] else 1, a["name"]))

    # Task queue summary
    pending_tasks = sum(1 for t in _TASKS.values() if t["status"] == "pending")
    in_progress_tasks = sum(1 for t in _TASKS.values() if t["status"] == "in_progress")

    return json.dumps({
        "agents": agents_list,
        "total_agents": len(agents_list),
        "available_agents": sum(1 for a in agents_list if a["is_available"]),
        "task_queue_summary": {
            "pending": pending_tasks,
            "in_progress": in_progress_tasks,
            "total_tasks": len(_TASKS),
        },
        "capability_filter": required_caps if required_caps else "none",
        "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    })


@mcp.tool()
async def complete_task(task_id: str, result: str, success: bool = True, api_key: str = "") -> str:
    """Mark a task as complete with results, or as failed with error details."""
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return json.dumps({"error": msg, "upgrade_url": "https://meok.ai/pricing"})
    if not _check_rate(api_key or "anon"):
        return json.dumps({"error": "Rate limit exceeded. Try again in 60 seconds."})

    task = _TASKS.get(task_id)
    if not task:
        return json.dumps({"error": f"Task '{task_id}' not found"})

    if task["status"] in ["completed", "cancelled"]:
        return json.dumps({"error": f"Task already '{task['status']}' - cannot modify"})

    if task["status"] not in ["in_progress", "assigned"]:
        return json.dumps({"error": f"Task is '{task['status']}' - must be in_progress or assigned to complete"})

    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    if success:
        task["status"] = "completed"
        task["result"] = result
        task["completed_at"] = now_iso
        task["history"].append({"event": "completed", "timestamp": now_iso})
    else:
        task["status"] = "failed"
        task["error"] = result
        task["completed_at"] = now_iso
        task["history"].append({"event": "failed", "reason": result[:200], "timestamp": now_iso})

    # Update agent metrics
    if task["assigned_agent"]:
        agent = _AGENTS.get(task["assigned_agent"])
        if agent:
            agent["current_tasks"] = max(0, agent["current_tasks"] - 1)
            if agent["current_tasks"] < agent["max_concurrent"]:
                agent["status"] = "available"
            if success:
                agent["completed_total"] += 1
                # Update average completion time
                if task["started_at"]:
                    try:
                        from datetime import datetime
                        started = datetime.strptime(task["started_at"], "%Y-%m-%dT%H:%M:%SZ")
                        completed = datetime.strptime(now_iso, "%Y-%m-%dT%H:%M:%SZ")
                        duration = (completed - started).total_seconds()
                        # Running average
                        prev_avg = agent["avg_completion_seconds"]
                        n = agent["completed_total"]
                        agent["avg_completion_seconds"] = round(((prev_avg * (n - 1)) + duration) / n, 0)
                    except Exception:
                        pass

    # Calculate duration
    duration_seconds = None
    if task["started_at"] and task["completed_at"]:
        try:
            from datetime import datetime
            started = datetime.strptime(task["started_at"], "%Y-%m-%dT%H:%M:%SZ")
            completed = datetime.strptime(task["completed_at"], "%Y-%m-%dT%H:%M:%SZ")
            duration_seconds = round((completed - started).total_seconds(), 0)
        except Exception:
            pass

    return json.dumps({
        "task_id": task_id,
        "title": task["title"],
        "status": task["status"],
        "success": success,
        "result": result if success else None,
        "error": result if not success else None,
        "assigned_agent": task["assigned_agent"],
        "duration_seconds": duration_seconds,
        "completed_at": now_iso,
    })


if __name__ == "__main__":
    mcp.run()
