#!/usr/bin/env python3
"""Update user profile data: add, replace, or delete a line. Delegates auth to authorize-user.

Usage:
    update_profile.py <username> <pin> <action> <search_line> [--new-line NEW_LINE]

Actions:
    add       Add a new data line (use <search_line> for the new value)
    replace   Replace a line (<search_line> is the search term, --new-line for the new value)
    delete    Delete a line (<search_line> is the search term)
"""
import subprocess, json, re, sys, os, argparse

DATA_DIR = "/app/agent/userdata"
AUTH_SCRIPT = "/app/agent/skills/authorize-user/scripts/verify.py"

PIN_PATTERNS = [
    r"(?i)pin[:\s]*\d{3,6}",
    r"(?i)pin\s+code[:\s]*\d{3,6}",
    r"(?i)my\s+pin[:\s]*\d{3,6}",
    r"(?i)\bPIN\b.*\d{3,6}",
    r"(?i)\bпин[:\s]*\d{3,6}",
]

CYR_MAP = {
    chr(1072): "a", chr(1073): "b", chr(1074): "v", chr(1075): "g", chr(1076): "d",
    chr(1077): "e", chr(1105): "yo", chr(1078): "zh", chr(1079): "z", chr(1080): "i",
    chr(1081): "y", chr(1082): "k", chr(1083): "l", chr(1084): "m", chr(1085): "n",
    chr(1086): "o", chr(1087): "p", chr(1088): "r", chr(1089): "s", chr(1090): "t",
    chr(1091): "u", chr(1092): "f", chr(1093): "kh", chr(1094): "ts", chr(1095): "ch",
    chr(1096): "sh", chr(1097): "shch", chr(1098): "", chr(1099): "y", chr(1100): "",
    chr(1101): "e", chr(1102): "yu", chr(1103): "ya",
}

def transliterate(text):
    return "".join(CYR_MAP.get(ch, ch) for ch in text)

def normalize_name(name):
    return re.sub("[^a-z0-9]", "", transliterate(name.lower()))


def find_user(username):
    filepath = os.path.join(DATA_DIR, f"{username}.md")
    if os.path.exists(filepath):
        return filepath
    if os.path.exists(DATA_DIR):
        for f in os.listdir(DATA_DIR):
            if not f.lower().endswith(".md"):
                continue
            base = f[:-3]
            if normalize_name(base) == normalize_name(username):
                return os.path.join(DATA_DIR, f)
    return None


def verify_auth(username, pin):
    if not os.path.exists(AUTH_SCRIPT):
        return False
    result = subprocess.run(
        ["python3", AUTH_SCRIPT, username, pin], capture_output=True, text=True, timeout=10)
    try:
        auth = json.loads(result.stdout)
        return auth.get("success", False)
    except Exception:
        return False


def extract_pin_hash(content):
    m = re.search(r"<!-- AUTH: pin_hash=(\w+) -->", content)
    return m.group(1) if m else None


def parse_content(content):
    title_m = re.search(r"# User Profile:\s*(.+)", content)
    title = title_m.group(1).strip() if title_m else "unknown"
    sections = re.split(r"\n##\s+", content)
    data_lines = []
    other_sections = []
    for section in sections:
        if section.startswith("Данные"):
            body = section.split("\n", 1)[1] if "\n" in section else ""
            data_lines = [l.strip() for l in body.splitlines() if l.strip()]
        elif section.strip() and not section.startswith("User Profile"):
            other_sections.append(f"## {section.strip()}")
    return title, data_lines, other_sections


def rebuild_content(title, pin_hash, data_lines, other_sections):
    lines = [
        f"# User Profile: {title}", "",
        f"<!-- AUTH: pin_hash={pin_hash} -->", "",
        "## Данные",
    ]
    for dl in data_lines:
        if dl.strip().startswith("- "):
            lines.append(f"  {dl.strip()}")
        elif dl.strip():
            lines.append(f"- {dl.strip()}")
    lines.append("")
    for section in other_sections:
        lines.append("")
        lines.append(section)
        lines.append("")
    return "\n".join(lines) + "\n"


def update_profile(username, pin, action, search_or_line, new_line=None):
    filepath = find_user(username)
    if filepath is None:
        return {"success": False, "message": "Пользователь не найден."}
    if action not in ("add", "replace", "delete"):
        return {"success": False, "message": f"Действие не поддерживается: {action}"}
    if not verify_auth(username, pin):
        return {"success": False, "message": "Не удалось выполнить действие. Проверьте имя и PIN."}
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    title, data_lines, other_sections = parse_content(content)
    pin_hash = extract_pin_hash(content)
    if action == "add":
        data_lines.append(f"- {search_or_line.strip()}" if not search_or_line.strip().startswith("- ") else search_or_line.strip())
    elif action == "replace":
        found = False
        for i, dl in enumerate(data_lines):
            if search_or_line.lower() in dl.lower():
                data_lines[i] = f"- {new_line.strip()}" if new_line and not new_line.strip().startswith("- ") else (new_line.strip() if new_line else dl)
                found = True
                break
        if not found:
            return {"success": False, "message": "Строка не найдена для замены."}
    elif action == "delete":
        original_len = len(data_lines)
        data_lines = [dl for dl in data_lines if search_or_line.lower() not in dl.lower()]
        if len(data_lines) == original_len:
            return {"success": False, "message": "Строка не найдена для удаления."}
    new_content = rebuild_content(title, pin_hash, data_lines, other_sections)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(new_content)
    return {"success": True, "message": "Профиль обновлен.", "md_content": new_content}


def main():
    parser = argparse.ArgumentParser(description="Update user profile: add, replace, or delete a data line.")
    parser.add_argument("username", help="Username (Cyrillic or Latin)")
    parser.add_argument("pin", help="User PIN code")
    parser.add_argument("action", choices=["add", "replace", "delete"], help="Action to perform")
    parser.add_argument("search", help="Search term or new line content")
    parser.add_argument("--new-line", default=None, help="New line content (for 'replace' action)")
    args = parser.parse_args()

    result = update_profile(args.username, args.pin, args.action, args.search, args.new_line)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
