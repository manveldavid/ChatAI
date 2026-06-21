#!/usr/bin/env python3
"""Register new user and save data to markdown file.
Delegates PIN registration to authorize-user skill.

Usage:
    register_user.py <username> <pin> [--data JSON_ARRAY]
    register_user.py <username> <pin> "line1" "line2" ...
"""
import subprocess, sys, os, json, re, argparse, hashlib

DATA_DIR = "/app/agent/userdata"
AUTH_REGISTER = "/app/agent/skills/authorize-user/scripts/register.py"

PIN_PATTERNS = [
    r'(?i)pin[:\s]*\d{3,6}',
    r'(?i)pin\s+code[:\s]*\d{3,6}',
    r'(?i)my\s+pin[:\s]*\d{3,6}',
    r'(?i)password[:\s]*\S{4,}',
    r'(?i)passwd[:\s]*\S{4,}',
    r'(?i)\bpin\b.*\d{4}\b',
]


def contains_pin_plaintext(data_lines, pin):
    for line in data_lines:
        if pin in line:
            return True, f"Строка содержит PIN в открытом виде: \'{line}\'"
        for pattern in PIN_PATTERNS:
            if re.search(pattern, line):
                return True, f"Строка содержит подозрительный паттерн: \'{line}\'"
    return False, ""


def register_user(username, pin, data_lines):
    os.makedirs(DATA_DIR, exist_ok=True)

    if not pin.isdigit() or len(pin) < 4:
        return {"success": False, "message": "PIN должен состоять минимум из 4 цифр."}

    contains_pin, error_msg = contains_pin_plaintext(data_lines, pin)
    if contains_pin:
        return {"success": False, "message": f"Отказ: {error_msg}. PIN нельзя хранить в открытом виде."}

    # Step 1: Register in authorize-user
    result = subprocess.run(
        ["python3", AUTH_REGISTER, username, pin],
        capture_output=True, text=True, timeout=10
    )
    try:
        auth = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"success": False, "message": "Ошибка системы авторизации."}

    if not auth.get("success"):
        err = auth.get("error", "unknown")
        if err == "user_exists":
            return {"success": False, "message": f"Пользователь \'{username}\' уже существует. Выберите другое имя."}
        return {"success": False, "message": f"Ошибка регистрации: {err}"}

    owner = auth["owner"]
    pin_hash = auth["owner_hash"]

    # Step 2: Create profile markdown
    filepath = os.path.join(DATA_DIR, f"{owner}.md")
    lines = [
        f"# User Profile: {owner}",
        "",
        f"<!-- AUTH: pin_hash={pin_hash} -->",
        "",
        "## Данные",
    ]
    for dl in data_lines:
        if dl.strip():
            lines.append(f"- {dl.strip()}")
    lines.append("")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return {"success": True, "message": f"Профиль \'{owner}\' создан. PIN: {pin}. Запомните его!", "owner": owner}


def main():
    parser = argparse.ArgumentParser(description="Register new user and create profile.")
    parser.add_argument("username", help="Username (Cyrillic or Latin)")
    parser.add_argument("pin", help="User PIN code (min 4 digits)")
    parser.add_argument("--data", nargs="*", default=[], help="Data lines as JSON string or positional args")
    args = parser.parse_args()

    # Allow data_lines from --data or positional args after pin
    # If user passed just username and pin, data_lines is []
    # If they want to pass data lines, they can use --data "line1" "line2"
    data_lines = args.data if args.data else []
    
    result = register_user(args.username, args.pin, data_lines)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
