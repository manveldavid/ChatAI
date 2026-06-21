#!/usr/bin/env python3
"""
Container Health Check & Diagnostics
Arguments: [quick|full|network] (default: quick)
Outputs structured JSON to stdout for the AI agent to process.
"""

import sys
from pathlib import Path
import os
import subprocess
import json
import time
import datetime
import urllib.request
import socket

MODE = sys.argv[1] if len(sys.argv) > 1 else "quick"

def run_cmd(cmd, timeout=5):
    try:
        return subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, timeout=timeout).decode().strip()
    except Exception as e:
        return f"Error: {str(e)}"

def check_http(url, timeout=5):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return {"status": "ok", "code": resp.status}
    except Exception as e:
        return {"status": "critical", "error": str(e)}

def get_disk_info():
    try:
        output = run_cmd("df -h / /tmp /app 2>/dev/null")
        results = []
        for line in output.split('\n')[1:]:
            parts = line.split()
            if len(parts) >= 5:
                use_pct = int(parts[4].replace('%', ''))
                results.append({"mount": parts[5], "usage_percent": use_pct, "status": "warning" if use_pct > 80 else ("critical" if use_pct > 95 else "ok")})
        return results if results else [{"mount": "/", "usage_percent": -1, "status": "unknown"}]
    except: return [{"mount": "/", "status": "error"}]

def get_memory_info():
    try:
        total = run_cmd("grep MemTotal /proc/meminfo | awk '{print $2}'")
        avail = run_cmd("grep MemAvailable /proc/meminfo | awk '{print $2}'")
        if total and avail:
            t, a = int(total), int(avail)
            used = t - a if a <= t else t
            pct = round((used / t) * 100)
            return {"total_mb": round(t/1024), "used_mb": round(used/1024), "usage_percent": pct, "status": "warning" if pct > 80 else ("critical" if pct > 95 else "ok")}
        return {"status": "unknown"}
    except: return {"status": "error"}

def get_cpu_load():
    try:
        load = os.getloadavg()
        # Rough estimation: load[0] is 1-min avg. For 1 CPU, 1.0 = 100%.
        ncpu = os.cpu_count() or 1
        pct = round((load[0] / ncpu) * 100)
        return {"load_1m": load[0], "cores": ncpu, "usage_percent": pct, "status": "warning" if pct > 80 else "ok"}
    except: return {"status": "unknown"}

def check_network():
    results = {}
    ip = run_cmd("curl -s --connect-timeout 3 ifconfig.me 2>/dev/null || echo 'unavailable'")
    results["external_ip"] = ip
    
    or_res = check_http("https://openrouter.ai/api/v1/models", timeout=5)
    results["openrouter"] = or_res
    
    dns = run_cmd("nslookup google.com 2>&1 | head -2")
    results["dns"] = "ok" if "Address" in dns else "critical"
    
    return results

def check_python_env():
    try:
        import sys as s
        packages = []
        try:
            import requests; packages.append("requests")
        except: pass
        try:
            import psutil; packages.append("psutil")
        except: pass
        try:
            import beautifulsoup4; packages.append("bs4")
        except: pass
        return {"version": s.version.split()[0], "packages": packages, "status": "ok"}
    except: return {"status": "error"}

def check_skills_inventory():
    skills_dir = str(Path(__file__).parent.parent.parent)
    skills = []
    if os.path.exists(skills_dir):
        for d in os.listdir(skills_dir):
            if os.path.isdir(os.path.join(skills_dir, d)):
                skills.append(d)
    return {"available": skills, "count": len(skills), "status": "ok"}

def check_file_structure():
    try:
        skills_root = Path(__file__).parent.parent.parent
        return {
            "skills_dir_exists": skills_root.exists(),
            "skills_count": len([d for d in skills_root.iterdir() if d.is_dir()]),
            "status": "ok"
        }
    except: return {"status": "error"}

def run_full_check():
    report = {
        "success": True,
        "timestamp": datetime.datetime.now().isoformat(),
        "mode": MODE,
        "checks": {
            "disk": get_disk_info(),
            "memory": get_memory_info(),
            "cpu": get_cpu_load(),
            "network": check_network(),
            "python": check_python_env(),
            "skills": check_skills_inventory(),
            "files": check_file_structure()
        },
        "warnings": [],
        "critical": False
    }
    
    # Gather warnings
    for section, data in report["checks"].items():
        if isinstance(data, list):
            for item in data:
                if item.get("status") == "warning":
                    report["warnings"].append(f"{section}: {item.get('mount', 'unknown')} approaching limits")
                elif item.get("status") == "critical":
                    report["critical"] = True
                    report["warnings"].append(f"{section}: {item.get('mount', 'unknown')} CRITICAL")
        elif isinstance(data, dict):
            if data.get("status") == "warning":
                report["warnings"].append(f"{section}: warning")
            elif data.get("status") == "critical":
                report["critical"] = True
                report["warnings"].append(f"{section}: CRITICAL")
                
    return report

def run_quick_check():
    return {
        "success": True,
        "timestamp": datetime.datetime.now().isoformat(),
        "mode": "quick",
        "checks": {
            "disk": get_disk_info(),
            "python": check_python_env(),
            "uptime": run_cmd("uptime")
        }
    }

def run_network_check():
    return {
        "success": True,
        "timestamp": datetime.datetime.now().isoformat(),
        "mode": "network",
        "checks": {
            "network": check_network()
        }
    }

if MODE == "full":
    print(json.dumps(run_full_check(), indent=2, default=str))
elif MODE == "network":
    print(json.dumps(run_network_check(), indent=2, default=str))
else:
    print(json.dumps(run_quick_check(), indent=2, default=str))
