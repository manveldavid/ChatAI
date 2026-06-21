#!/usr/bin/env python3
"""
Central user registration.
Usage: register.py <username> <pin>
Returns JSON with success status.
"""
import hashlib, json, os, sys

DATA_DIR = "/app/agent/auth"
USERS_FILE = os.path.join(DATA_DIR, "users.json")

CYR_TO_LAT = {
    chr(1072): 'a', chr(1073): 'b', chr(1074): 'v', chr(1075): 'g', chr(1076): 'd',
    chr(1077): 'e', chr(1105): 'yo', chr(1078): 'zh', chr(1079): 'z', chr(1080): 'i',
    chr(1081): 'y', chr(1082): 'k', chr(1083): 'l', chr(1084): 'm', chr(1085): 'n',
    chr(1086): 'o', chr(1087): 'p', chr(1088): 'r', chr(1089): 's', chr(1090): 't',
    chr(1091): 'u', chr(1092): 'f', chr(1093): 'kh', chr(1094): 'ts', chr(1095): 'ch',
    chr(1096): 'sh', chr(1097): 'shch', chr(1098): '', chr(1099): 'y', chr(1100): '',
    chr(1101): 'e', chr(1102): 'yu', chr(1103): 'ya',
}


def transliterate(text):
    result = []
    for ch in text:
        lower = ch.lower()
        if lower in CYR_TO_LAT:
            latin = CYR_TO_LAT[lower]
            if ch.isupper():
                latin = latin.upper()
            result.append(latin)
        else:
            result.append(ch)
    return "".join(result)


def normalize(username):
    return transliterate(username.strip()).lower()


def hash_pin(pin):
    return hashlib.sha256(str(pin).strip().encode("utf-8")).hexdigest()


def load_users():
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_users(users):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def main():
    if len(sys.argv) < 3:
        print(json.dumps({"success": False, "error": "Usage: register.py <username> <pin>"}))
        return

    username = sys.argv[1]
    pin = sys.argv[2]
    norm = normalize(username)
    users = load_users()

    if norm in users:
        print(json.dumps({"success": False, "error": "user_exists"}))
        return

    users[norm] = {"pin_hash": hash_pin(pin)}
    save_users(users)
    print(json.dumps({"success": True, "owner": norm, "owner_hash": hash_pin(pin), "message": f"User {norm!r} registered"}))


if __name__ == "__main__":
    main()
