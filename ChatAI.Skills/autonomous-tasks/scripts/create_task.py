#!/usr/bin/env python3
"""Create a new autonomous task file. Verifies owner_hash before creation."""

import argparse, os, json, sys, time, uuid
from datetime import datetime

ACTIVE_DIR = "/app/agent/tasks/active"
COMPLETED_DIR = "/app/agent/tasks/completed"


def get_lock_path(filename):
    """Get per-task lock file path in completed/ directory."""
    return os.path.join(COMPLETED_DIR, f"{filename}.lock")


def create_lock_file(filename, task_name, current_task, previous_context, owner_hash):
    """Create per-task lock file in completed/ directory."""
    os.makedirs(COMPLETED_DIR, exist_ok=True)
    lock_path = get_lock_path(filename)
    lock_data = {
        "task_name": task_name,
        "filename": filename,
        "current_task": current_task,
        "previous_context": previous_context,
        "owner_hash": owner_hash,
        "timestamp": datetime.now().isoformat()
    }
    with open(lock_path, "w", encoding="utf-8") as f:
        json.dump(lock_data, f, indent=2, ensure_ascii=False)
    return lock_path


def remove_lock_file(filename):
    """Remove per-task lock file from completed/ directory."""
    lock_path = get_lock_path(filename)
    if os.path.exists(lock_path):
        os.remove(lock_path)
        return True
    return False


def verify_owner_hash(owner_hash):
    DATA_FILE = "/app/agent/auth/users.json"
    if not os.path.exists(DATA_FILE):
        return False, None
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        users = json.load(f)
    for username, data in users.items():
        if data.get("pin_hash") == owner_hash:
            return True, username
    return False, None


def create_task(owner, owner_hash, task_name, global_objective, previous_context, current_task, body="", filename=None, remove_parent_lock=None):
    valid, verified_owner = verify_owner_hash(owner_hash)
    if not valid:
        print("Error: invalid owner_hash", file=sys.stderr)
        return print(json.dumps({"success": False, "error": "Invalid owner_hash"}))

    os.makedirs(ACTIVE_DIR, exist_ok=True)
    if not filename:
        filename = f"task-{int(time.time())}-{uuid.uuid4().hex[:6]}.md"
    filepath = os.path.join(ACTIVE_DIR, filename)

    P = chr(39)
    NL = chr(10)
    lines = ["---"]
    lines.append(f"task_filename: {P}{filename}{P}")
    lines.append(f"task_name: {P}{task_name}{P}")
    lines.append(f"owner: {P}{owner}{P}")
    lines.append(f"owner_hash: {owner_hash}")
    lines.append(f"created_at: {P}{datetime.now().isoformat()}{P}")
    lines.append("status: active")
    lines.append(f"global_objective: {P}{global_objective}{P}")
    lines.append("previous_context: |")
    for ln in previous_context.strip().splitlines():
        lines.append(f"  {ln}")
    lines.append("current_task: |")
    for ln in current_task.strip().splitlines():
        lines.append(f"  {ln}")
    lines.append("---")
    if body.strip():
        lines.append("")
        lines.append(body.strip())
    lines.append("")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(NL.join(lines))
        f.write(NL)

    # Create per-task lock file in completed/
    lock_path = create_lock_file(filename, task_name, current_task, previous_context, owner_hash)

    # Optionally remove parent task lock (when continuing a chain)
    if remove_parent_lock:
        remove_lock_file(remove_parent_lock)

    print(f"Task created: {filepath}")
    return print(json.dumps({"success": True, "filepath": filepath, "filename": filename, "lock_file": lock_path}, ensure_ascii=False))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--owner", required=True)
    p.add_argument("--owner-hash", required=True)
    p.add_argument("--task-name", required=True)
    p.add_argument("--global-objective", required=True)
    p.add_argument("--previous-context", default="New task. No previous steps.")
    p.add_argument("--current-task", required=True)
    p.add_argument("--body", default="")
    p.add_argument("--filename", default=None)
    p.add_argument("--remove-parent-lock", default=None,
        help="Filename of parent task whose lock should be removed after creating this task.")
    args = p.parse_args()
    create_task(args.owner, args.owner_hash, args.task_name, args.global_objective,
                args.previous_context, args.current_task, args.body, args.filename,
                args.remove_parent_lock)


if __name__ == "__main__":
    main()
