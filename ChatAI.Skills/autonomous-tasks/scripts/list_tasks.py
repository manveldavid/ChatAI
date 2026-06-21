#!/usr/bin/env python3
"""List tasks for an authenticated user. Verifies owner_hash."""

import argparse, os, json, glob
from pathlib import Path

ACTIVE_DIR = os.environ.get("AGENT_TASKS_ACTIVE", str(Path(__file__).parent.parent / "active"))
COMPLETED_DIR = os.environ.get("AGENT_TASKS_COMPLETED", str(Path(__file__).parent.parent / "completed"))


def parse_task_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    parts = content.split("---")
    if len(parts) < 3: return {}
    fm_str, body = parts[1], "---".join(parts[2:]).strip()
    result, current_key, block_lines, is_block = {}, None, [], False
    def save():
        nonlocal current_key, block_lines, is_block
        if current_key:
            result[current_key] = "\n".join(block_lines) if is_block else " ".join(block_lines).strip().strip(chr(39))
            current_key, block_lines, is_block = None, [], False
    for line in fm_str.splitlines():
        s = line.strip()
        if not s and is_block:
            block_lines.append(""); continue
        if (":" in s) and not line.startswith("  ") and not line.startswith("\t"):
            save()
            k, v = s.split(":", 1)[0].strip(), s.split(":", 1)[1].strip()
            if v == "|": current_key, is_block, block_lines = k, True, []
            else: current_key, is_block, block_lines = k, False, [v]
        elif is_block and line.startswith("  "):
            block_lines.append(line[2:])
    save()
    result["_body"] = body
    return result


def list_tasks(owner_hash, verbose=False):
    out = {"owner_hash": owner_hash, "active": [], "completed": [], "processing": []}

    # Read per-task lock files in completed/ (*.lock)
    lock_pattern = os.path.join(COMPLETED_DIR, "*.lock")
    for lock_path in sorted(glob.glob(lock_pattern)):
        fname = os.path.basename(lock_path)
        # Skip lock files that do not correspond to .md files in active/
        # (stale locks from completed tasks that somehow were not removed)
        md_filename = fname[:-5]  # remove ".lock"
        if not md_filename.endswith(".md"):
            continue
        try:
            with open(lock_path, "r", encoding="utf-8") as f:
                lock_data = json.load(f)
            if lock_data.get("owner_hash") == owner_hash:
                # Only include if the actual md file still exists in active/
                active_md = os.path.join(ACTIVE_DIR, md_filename)
                if os.path.exists(active_md):
                    out["processing"].append(lock_data)
        except:
            pass

    for d, key in [(ACTIVE_DIR, "active"), (COMPLETED_DIR, "completed")]:
        if not os.path.exists(d): continue
        for fname in sorted(os.listdir(d)):
            if not fname.endswith(".md"): continue
            fm = parse_task_file(os.path.join(d, fname))
            if fm.get("owner_hash") == owner_hash:
                entry = {"filename": fname}
                for k in ["task_filename", "task_name", "global_objective", "status", "created_at", "previous_context", "current_task"]:
                    if k in fm: entry[k] = fm[k]
                if key == "completed":
                    for k in ["completion_report", "completed_at"]:
                        if k in fm: entry[k] = fm[k]
                out[key].append(entry)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--owner-hash", required=True)
    p.add_argument("--verbose", action="store_true")
    list_tasks(p.parse_args().owner_hash, p.parse_args().verbose)


if __name__ == "__main__":
    main()