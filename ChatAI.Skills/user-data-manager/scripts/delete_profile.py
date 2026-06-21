#!/usr/bin/env python3
"""Delete user profile with auth delegated to authorize-user.

Usage:
    delete_profile.py <username> <pin>
"""
import subprocess, json, os, sys, argparse

DATA_DIR = "/app/agent/userdata"
AUTH_SCRIPT = "/app/agent/skills/authorize-user/scripts/verify.py"


def find_user(username):
    filepath = os.path.join(DATA_DIR, f"{username}.md")
    if os.path.exists(filepath):
        return filepath
    if os.path.exists(DATA_DIR):
        for f in os.listdir(DATA_DIR):
            if not f.lower().endswith(".md"):
                continue
            base = f[:-3]
            if base.lower() == username.lower():
                return os.path.join(DATA_DIR, f)
    return None


def delete_profile(username, pin):
    filepath = find_user(username)
    if filepath is None:
        return {"success": False, "message": "Пользователь не найден."}
    if not os.path.exists(AUTH_SCRIPT):
        return {"success": False, "message": "Система авторизации недоступна."}
    result = subprocess.run(
        ["python3", AUTH_SCRIPT, username, pin], capture_output=True, text=True, timeout=10)
    try:
        auth = json.loads(result.stdout)
    except Exception:
        return {"success": False, "message": "Не удалось выполнить действие."}
    if not auth.get("success"):
        return {"success": False, "message": "Не удалось выполнить действие. Проверьте имя пользователя и PIN."}
    os.remove(filepath)
    return {"success": True, "message": "Профиль удален."}


def main():
    parser = argparse.ArgumentParser(description="Delete user profile after PIN verification.")
    parser.add_argument("username", help="Username (Cyrillic or Latin)")
    parser.add_argument("pin", help="User PIN code")
    args = parser.parse_args()

    result = delete_profile(args.username, args.pin)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
