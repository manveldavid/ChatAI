#!/usr/bin/env python3
"""Parse frontmatter from a task file and output JSON."""

import argparse, os, json, re, sys


def parse_task_file(filepath):
    """Parse a task file with YAML frontmatter into a dict."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Find everything between first --- and last --- before body
    # Strategy: collect all lines until we hit a line that is "---" 
    # and the NEXT non-indent line does not look like a YAML key
    lines_all = content.splitlines()
    fm_lines = []
    in_fm = False
    body_lines = []
    in_body = False
    
    i = 0
    if lines_all[0].strip() == "---":
        in_fm = True
        i = 1
    
    while i < len(lines_all):
        line = lines_all[i]
        if in_fm:
            if line.strip() == "---":
                in_fm = False
                i += 1
                continue
            fm_lines.append(line)
        else:
            body_lines.append(line)
        i += 1

    # Parse frontmatter lines into dict
    result = {}
    current_key = None
    current_value = []
    current_is_block = False
    indent_for_block = 0
    
    def save_field():
        nonlocal current_key, current_value, current_is_block
        if current_key:
            if current_is_block:
                val = chr(10).join(current_value).strip()
            else:
                val = " ".join(current_value).strip()
                if (val.startswith(chr(39)) and val.endswith(chr(39))):
                    val = val[1:-1]
                elif (val.startswith(chr(34)) and val.endswith(chr(34))):
                    val = val[1:-1]
            result[current_key] = val
            current_key = None
            current_value = []
            current_is_block = False
    
    for line in fm_lines:
        stripped = line.strip()
        if not stripped:
            if current_is_block:
                current_value.append("")
            continue
        if ":" in stripped and not stripped.startswith("  "):
            # Save previous field
            save_field()
            key, sep, val = stripped.partition(":")
            key = key.strip()
            val = val.strip()
            if val == "|":
                current_key = key
                current_is_block = True
                current_value = []
                # Determine indent level from next content line
            else:
                current_key = key
                current_is_block = False
                current_value = [val]
        elif current_is_block and (line.startswith("  ") or stripped == ""):
            # Block continuation
            if stripped == "" and current_value and current_value[-1] == "":
                # Skip consecutive empty lines in block
                pass
            else:
                current_value.append(line[2:] if line.startswith("  ") else stripped)
        elif not current_is_block:
            # Continuation of scalar value
            if stripped.startswith("- ") or ":" in stripped:
                pass
            else:
                current_value.append(stripped)
    
    save_field()
    result["_body"] = chr(10).join(body_lines).strip()
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("filepath")
    args = p.parse_args()
    data = parse_task_file(args.filepath)
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()