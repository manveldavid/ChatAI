#!/usr/bin/env python3
"""Restore completed task to active, or remove completed report. Verifies owner_hash."""

import argparse, os, json
from pathlib import Path

ACTIVE_DIR = os.environ.get("AGENT_TASKS_ACTIVE", str(Path(__file__).parent.parent / "active"))
COMPLETED_DIR = os.environ.get("AGENT_TASKS_COMPLETED", str(Path(__file__).parent.parent / "completed"))


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


def verify_owner(filepath, owner_hash):
    with open(filepath, "r", encoding="utf-8") as f:
        return f"owner_hash: {owner_hash}" in f.read()


def restore_task(filename, owner_hash):
    src = os.path.join(COMPLETED_DIR, filename)
    if not os.path.exists(src):
        return print(json.dumps({"success": False, "error": "Task not found"}, ensure_ascii=False))
    if not verify_owner(src, owner_hash):
        return print(json.dumps({"success": False, "error": "Owner verification failed"}, ensure_ascii=False))

    with open(src, "r", encoding="utf-8") as f: content = f.read()
    parts = content.split("---")
    fm, body = parts[1], "---".join(parts[2:]).strip().split("---")[0].strip()

    fm_lines, skip = [], None
    for l in fm.splitlines():
        ls = l.strip()
        if ls.startswith(("completion_report:", "completed_at:")): skip = True; continue
        if skip and l.startswith("  "): continue
        if skip: skip = False
        if ls.startswith("status:"): continue
        fm_lines.append(l)
    fm_lines.append("status: active")

    dest = os.path.join(ACTIVE_DIR, filename)
    NL = chr(10)
    with open(dest, "w", encoding="utf-8") as f:
        f.write("---" + NL)
        f.write(NL.join(fm_lines))
        f.write(NL + "---" + NL + (NL + body + NL if body else ""))
    os.remove(src)

    # Create a lock file for the restored task (it needs to be processed by agent)
    lock_data = {"task_filename": filename, "restored": True, "owner_hash": owner_hash, "timestamp": __import__("datetime").datetime.now().isoformat()}
    lock_path = get_lock_path(filename)
    with open(lock_path, "w", encoding="utf-8") as f:
        json.dump(lock_data, f, indent=2, ensure_ascii=False)

    return print(json.dumps({"success": True, "filepath": dest}, ensure_ascii=False))


def remove_completed(filename, owner_hash):
    src = os.path.join(COMPLETED_DIR, filename)
    if not os.path.exists(src):
        return print(json.dumps({"success": False, "error": "Task not found"}, ensure_ascii=False))
    if not verify_owner(src, owner_hash):
        return print(json.dumps({"success": False, "error": "Owner verification failed"}, ensure_ascii=False))
    os.remove(src)
    # Also remove any leftover lock file
    remove_lock_file(filename)
    return print(json.dumps({"success": True}, ensure_ascii=False))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--action", required=True, choices=["restore", "remove"])
    p.add_argument("--filename", required=True)
    p.add_argument("--owner-hash", required=True)
    args = p.parse_args()
    if args.action == "restore": restore_task(args.filename, args.owner_hash)
    else: remove_completed(args.filename, args.owner_hash)


if __name__ == "__main__":
    main()