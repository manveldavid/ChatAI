#!/usr/bin/env python3
"""Verify user PIN via authorize-user, then return profile content.
Delegates authentication to authorize-user skill.

Usage:
    verify_pin.py <username> <pin>
"""
import subprocess, json, os, sys, argparse

DATA_DIR = "/app/agent/userdata"


def find_user_file(username):
    """Find the user profile file by username (supports Cyrillic/Latin, case-insensitive)."""
    # Direct match
    filepath = os.path.join(DATA_DIR, f"{username}.md")
    if os.path.exists(filepath):
        return filepath

    if not os.path.exists(DATA_DIR):
        return None

    # Case-insensitive filename match
    for f in os.listdir(DATA_DIR):
        if not f.lower().endswith(".md"):
            continue
        if f.lower() == f"{username.lower()}.md":
            return os.path.join(DATA_DIR, f)

    return None


def verify_pin(username, pin):
    """Verify PIN via authorize-user, then return profile content."""
    AUTH_SCRIPT = "/app/agent/skills/authorize-user/scripts/verify.py"

    if not os.path.exists(AUTH_SCRIPT):
        return {"success": False, "message": "Система авторизации недоступна", "md_content": None}

    # Step 1: Delegate to authorize-user for PIN verification
    result = subprocess.run(
        ["python3", AUTH_SCRIPT, username, pin],
        capture_output=True, text=True, timeout=10
    )
    try:
        auth = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"success": False, "message": "Не удалось выполнить вход. Проверьте имя пользователя и PIN.", "md_content": None}

    if not auth.get("success"):
        return {"success": False, "message": "Не удалось выполнить вход. Проверьте имя пользователя и PIN.", "md_content": None}

    # Step 2: Auth passed, find and return profile
    owner = auth["owner"]
    filepath = find_user_file(owner)

    if filepath is None or not os.path.exists(filepath):
        return {"success": False, "message": "Не удалось получить данные профиля.", "md_content": None}

    with open(filepath, "r", encoding="utf-8") as f:
        md_content = f.read()

    return {"success": True, "message": f"Добро пожаловать, {owner}!", "md_content": md_content}


def main():
    parser = argparse.ArgumentParser(description="Verify user PIN and return profile data.")
    parser.add_argument("username", help="Username (Cyrillic or Latin)")
    parser.add_argument("pin", help="User PIN code")
    args = parser.parse_args()

    result = verify_pin(args.username, args.pin)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
