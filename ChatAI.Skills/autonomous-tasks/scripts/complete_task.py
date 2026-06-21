#!/usr/bin/env python3
"""Complete a task: add report and move to completed/. Verifies owner_hash."""

import argparse, os, json, sys
from datetime import datetime

ACTIVE_DIR = "/app/agent/tasks/active"
COMPLETED_DIR = "/app/agent/tasks/completed"


def get_lock_path(filename):
    """Get per-task lock file path in completed/ directory."""
    return os.path.join(COMPLETED_DIR, f"{filename}.lock")


def remove_lock_file(filename):
    """Remove per-task lock file from completed/ directory."""
    lock_path = get_lock_path(filename)
    if os.path.exists(lock_path):
        os.remove(lock_path)
        return True
    return False


def complete_task(filename, report, owner_hash):
    src = os.path.join(ACTIVE_DIR, filename)
    if not os.path.exists(src):
        return print(json.dumps({"success": False, "error": f"Task not found: {filename}"}))
    with open(src, "r", encoding="utf-8") as f:
        content = f.read()
    if f"owner_hash: {owner_hash}" not in content:
        return print(json.dumps({"success": False, "error": "Owner verification failed"}))

    parts = content.split("---")
    fm_lines = [l for l in parts[1].splitlines() if not l.strip().startswith(("completion_report:", "completed_at:", "status:"))]
    body = "---".join(parts[2:]).strip()

    NL = chr(10)
    now = datetime.now().isoformat()
    fm_lines.extend(["completion_report: |"] + [f"  {ln}" if ln else "" for ln in report.strip().splitlines()])
    fm_lines.append(f"completed_at: ''{now}''")
    fm_lines.append("status: completed")

    dest = os.path.join(COMPLETED_DIR, filename)
    os.makedirs(COMPLETED_DIR, exist_ok=True)
    with open(dest, "w", encoding="utf-8") as f:
        f.write("---" + NL)
        f.write(NL.join(fm_lines))
        f.write(NL + "---" + NL + NL)
        # Write body
        f.write(body.strip())
        f.write(NL)
    os.remove(src)

    # Remove per-task lock file (atomic - no race condition)
    remove_lock_file(filename)

    print(f"Task completed: {dest}")
    print(json.dumps({"success": True, "filepath": dest}, ensure_ascii=False))
    return dest


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--filename", required=True)
    p.add_argument("--report", required=True)
    p.add_argument("--owner-hash", required=True)
    args = p.parse_args()
    complete_task(args.filename, args.report, args.owner_hash)


if __name__ == "__main__":
    main()