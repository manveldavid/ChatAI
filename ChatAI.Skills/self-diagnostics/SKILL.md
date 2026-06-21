---
name: self-diagnostics
description: Run self-diagnosis, health checks, and monitor container environment.
Use when I (the AI agent) want to check my own health, diagnose issues, monitor resources,
or understand my current environment state before executing complex tasks.
---

# Container Self-Diagnostics

This skill allows the AI agent to check its own health, diagnose problems, and monitor the container environment.

## When to Use

- Before starting a complex or long-running task to ensure the environment is healthy.
- When experiencing errors or unexpected behavior.
- Periodically for proactive monitoring.
- To gather system information (CPU, RAM, disk, network, Python packages).

## Diagnostics Script

### Health Check (`scripts/health_check.py`)

Run a comprehensive health check of the container.

```
RunPythonScript(
    scriptFullPath="/app/agent/skills/self-diagnostics/scripts/health_check.py",
    args=["full"]  # options: "quick", "full", "network"
)
```

**Arguments:**
- `quick` — Fast check: disk space, Python version, basic connectivity.
- `full` — Comprehensive check: CPU/RAM load, all disk mounts, network connectivity to key services (OpenRouter, GitHub), Python packages, skill inventory, file permissions.
- `network` — Only network diagnostics: ping tests, DNS, external IP.

**Output:**
A structured JSON/Markdown report to stdout:
```json
{
  "success": true,
  "timestamp": "...",
  "checks": {
    "disk": {"status": "ok", "usage_percent": 45},
    "memory": {"status": "ok", "total_mb": 2048, "used_mb": 512},
    "cpu": {"status": "ok", "load_percent": 12},
    "network": {"status": "ok", "openrouter": "reachable", "external_ip": "X.X.X.X"},
    "python": {"status": "ok", "packages": ["requests", "psutil"]},
    "skills": {"status": "ok", "available": ["ddg-search", "xlsx", "..."]}
  },
  "warnings": [],
  "critical": false
}
```

**Status meanings:**
- `"status": "ok"` — All normal, no action needed.
- `"status": "warning"` — Approaching limits (disk > 80%, high load), worth attention.
- `"status": "critical"` — Immediate action recommended (disk full, no network, service unreachable).

## Interpretation Guidelines

- If `critical` is true → **Stop non-essential work**, report the issue, and attempt self-recovery (free up disk space, restart a failed service, etc.).
- If `warnings` exist → Log them, consider taking preventive action (clean up old files, optimize memory usage).
- If all clear → Proceed with planned tasks.

You do not need to run this skill on every interaction. Use it judiciously when conditions warrant.


<scripts>
  <script name="scripts/health_check.py">
    <parameters_schema>{"type":"array","items":{"type":"string"}}</parameters_schema>
  </script>
</scripts>