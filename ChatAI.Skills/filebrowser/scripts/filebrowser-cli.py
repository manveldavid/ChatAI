#!/usr/bin/env python3
"""filebrowser-cli.py — CLI wrapper for the FileBrowser REST API client.

Dynamically loads '../references/filebrowser-client.py' and executes
commands via argv, printing JSON output.

Usage:
    python filebrowser-cli.py --url URL --user USER --pass PASS COMMAND [ARGS...]

Example:
    python filebrowser-cli.py --url http://localhost:8080 --user admin --pass admin list /
    python filebrowser-cli.py --url http://localhost:8080 --user admin --pass pass info /docs/readme.md
    python filebrowser-cli.py --url http://localhost:8080 --user admin --pass pass mkdirs /new/folder/path
    python filebrowser-cli.py --url http://localhost:8080 --user admin --pass pass upload /local/file.txt /remote/file.txt
    python filebrowser-cli.py --url http://localhost:8080 --user admin --pass pass download /remote/file.txt /local/download.txt
    python filebrowser-cli.py --url http://localhost:8080 --user admin --pass pass server-info
"""

import argparse
import importlib.util
import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Dynamic import of the client module
# ---------------------------------------------------------------------------
_CLIENT_PATH = str(
    Path(__file__).resolve().parent.parent / "references" / "filebrowser-client.py"
)

spec = importlib.util.spec_from_file_location("filebrowser_client", _CLIENT_PATH)
_client_mod = importlib.util.module_from_spec(spec)
sys.modules["filebrowser_client"] = _client_mod
spec.loader.exec_module(_client_mod)

FileBrowser = _client_mod.FileBrowser
FileBrowserError = _client_mod.FileBrowserError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _build_parser():
    parser = argparse.ArgumentParser(
        prog="filebrowser-cli",
        description="CLI for FileBrowser REST API"
    )
    parser.add_argument("--url", "-u", required=True, help="FileBrowser server URL (no trailing slash)")
    parser.add_argument("--user", required=True, help="Username")
    parser.add_argument("--pass", "-p", dest="password", required=True, help="Password")

    sub = parser.add_subparsers(dest="command", required=True, help="Command to execute")

    # ---- directory commands ----
    p = sub.add_parser("list", help="List directory contents")
    p.add_argument("path", nargs="?", default="/", help="Remote path (default /)")

    p = sub.add_parser("info", help="Get metadata for file/dir")
    p.add_argument("path", help="Remote path")

    p = sub.add_parser("exists", help="Check if path exists")
    p.add_argument("path", help="Remote path")

    p = sub.add_parser("mkdirs", help="Create directory and parents")
    p.add_argument("path", help="Remote directory path")

    # ---- file transfer ----
    p = sub.add_parser("upload", help="Upload a local file to remote")
    p.add_argument("local", help="Local file path")
    p.add_argument("remote", help="Remote file path")
    p.add_argument("--no-override", action="store_true", help="Do not overwrite existing file")

    p = sub.add_parser("upload-string", help="Upload a string as a file")
    p.add_argument("content", help="String content to upload")
    p.add_argument("remote", help="Remote file path")
    p.add_argument("--no-override", action="store_true")

    p = sub.add_parser("download", help="Download a remote file locally")
    p.add_argument("remote", help="Remote file path")
    p.add_argument("local", help="Local destination path")

    p = sub.add_parser("read-file", help="Read remote file as raw bytes (base64 output)")
    p.add_argument("path", help="Remote file path")

    # ---- mutating commands ----
    p = sub.add_parser("delete", help="Delete a file or directory")
    p.add_argument("path", help="Remote path")

    p = sub.add_parser("rename", help="Rename/move a file or directory")
    p.add_argument("source", help="Source path")
    p.add_argument("destination", help="Destination path")

    p = sub.add_parser("move", help="Move a file or directory (alias for rename)")
    p.add_argument("source", help="Source path")
    p.add_argument("destination", help="Destination path")

    p = sub.add_parser("copy", help="Copy a file or directory")
    p.add_argument("source", help="Source path")
    p.add_argument("destination", help="Destination path")

    # ---- shares ----
    p = sub.add_parser("create-share", help="Create a public share link")
    p.add_argument("path", help="Remote file/dir path")
    p.add_argument("--expire", default="", help="Expiration (e.g. 2024-12-31)")

    p = sub.add_parser("list-shares", help="List all public shares by current user")

    p = sub.add_parser("delete-share", help="Delete a public share")
    p.add_argument("hash", help="Share hash")

    # ---- server commands ----
    p = sub.add_parser("health-check", help="Check if server is reachable")

    p = sub.add_parser("server-info", help="Get server version and basic info")

    p = sub.add_parser("server-settings", help="Get full server configuration")

    p = sub.add_parser("disk-usage", help="Show disk usage")
    p.add_argument("path", nargs="?", default="/", help="Remote path (default /)")

    p = sub.add_parser("search", help="Search files by name")
    p.add_argument("query", help="Search query")
    p.add_argument("--path", default="/", help="Search starting path (default /)")

    p = sub.add_parser("download-archive", help="Download multiple files as ZIP")
    p.add_argument("paths", nargs="+", help="Remote paths")
    p.add_argument("--output", "-o", help="Local output path")

    # ---- user management (admin) ----
    p = sub.add_parser("list-users", help="List all users")

    p = sub.add_parser("create-user", help="Create a new user")
    p.add_argument("username")
    p.add_argument("password")
    p.add_argument("scope", nargs="?", default="/", help="Root scope (default /)")

    p = sub.add_parser("delete-user", help="Delete a user by ID")
    p.add_argument("user_id", type=int, help="User ID (integer)")

    p = sub.add_parser("change-password", help="Reset user password")
    p.add_argument("user_id", type=int)
    p.add_argument("new_password")

    # ---- sync & diff ----
    p = sub.add_parser("diff", help="Compare local vs remote directory")
    p.add_argument("local_path", help="Local directory")
    p.add_argument("remote_path", help="Remote directory")

    p = sub.add_parser("sync-to-remote", help="Sync local directory to remote")
    p.add_argument("local_path")
    p.add_argument("remote_path")
    p.add_argument("--delete-extra", action="store_true")
    p.add_argument("--dry-run", action="store_true")

    p = sub.add_parser("sync-from-remote", help="Sync remote directory to local")
    p.add_argument("remote_path")
    p.add_argument("local_path")
    p.add_argument("--delete-extra", action="store_true")
    p.add_argument("--dry-run", action="store_true")

    return parser


# ---------------------------------------------------------------------------
# Command dispatcher
# ---------------------------------------------------------------------------
def run_command(fb: FileBrowser, args_namespace):
    cmd = args_namespace.command
    a = args_namespace   # short alias

    # --- directory ---
    if cmd == "list":
        return {"items": fb.list(a.path)}

    elif cmd == "info":
        return fb.info(a.path)

    elif cmd == "exists":
        return {"exists": fb.exists(a.path)}

    elif cmd == "mkdirs":
        fb.mkdirs(a.path)
        return {"created": a.path}

    # --- file transfer ---
    elif cmd == "upload":
        local = Path(a.local).resolve()
        if not local.is_file():
            return _error(f"Local file not found: {local}")
        fb.upload(str(local), a.remote, override=not a.no_override)
        return {"uploaded": str(local), "remote": a.remote}

    elif cmd == "upload-string":
        fb.upload_string(a.content, a.remote, override=not a.no_override)
        return {"uploaded": len(a.content), "remote": a.remote}

    elif cmd == "download":
        dest = fb.download(a.remote, a.local)
        return {"downloaded": str(dest)}

    elif cmd == "read-file":
        data = fb.read_file(a.path)
        # Return as base64 for binary safety
        import base64
        return {
            "path": a.path,
            "size_bytes": len(data),
            "content_base64": base64.b64encode(data).decode()
        }

    # --- mutating ---
    elif cmd == "delete":
        fb.delete(a.path)
        return {"deleted": a.path}

    elif cmd == "rename" or cmd == "move":
        fb.rename(a.source, a.destination)
        return {"renamed": a.source, "to": a.destination}

    elif cmd == "copy":
        fb.copy(a.source, a.destination)
        return {"copied": a.source, "to": a.destination}

    # --- shares ---
    elif cmd == "create-share":
        return fb.create_share(a.path, expire=a.expire)

    elif cmd == "list-shares":
        return {"shares": fb.list_shares()}

    elif cmd == "delete-share":
        fb.delete_share(a.hash)
        return {"deleted_share": a.hash}

    # --- server ---
    elif cmd == "health-check":
        return {"healthy": fb.health_check()}

    elif cmd == "server-info":
        return fb.server_info()

    elif cmd == "server-settings":
        return fb.server_settings()

    elif cmd == "disk-usage":
        return fb.disk_usage(a.path)

    elif cmd == "search":
        return {"results": fb.search(a.query, getattr(a, "path", "/"))}

    elif cmd == "download-archive":
        dest = fb.download_archive(a.paths, a.output)
        if a.output:
            return {"downloaded": str(dest)}
        return {"note": "ZIP bytes not returned via CLI; use --output to save locally"}

    # --- users ---
    elif cmd == "list-users":
        return {"users": fb.list_users()}

    elif cmd == "create-user":
        user = fb.create_user(a.username, a.password, a.scope)
        return {"user": user}

    elif cmd == "delete-user":
        fb.delete_user(a.user_id)
        return {"deleted_user_id": a.user_id}

    elif cmd == "change-password":
        fb.change_user_password(a.user_id, a.new_password)
        return {"password_changed_user_id": a.user_id}

    # --- sync & diff ---
    elif cmd == "diff":
        return fb.diff(a.local_path, a.remote_path)

    elif cmd == "sync-to-remote":
        return fb.sync_local_to_remote(
            a.local_path, a.remote_path,
            delete_extra=a.delete_extra, dry_run=a.dry_run
        )

    elif cmd == "sync-from-remote":
        return fb.sync_remote_to_local(
            a.remote_path, a.local_path,
            delete_extra=a.delete_extra, dry_run=a.dry_run
        )

    return _error(f"Unknown command: {cmd}")


def _error(msg):
    return {"error": msg}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = _build_parser()
    args = parser.parse_args()

    # Instantiate client (login is automatic in __init__)
    try:
        fb = FileBrowser(args.url, args.user, args.password)
    except FileBrowserError as e:
        print(json.dumps(_error(f"Login failed: {e}"), indent=2))
        sys.exit(1)
    except Exception as e:
        print(json.dumps(_error(f"Login error: {str(e)}"), indent=2))
        sys.exit(1)

    # Execute command
    try:
        result = run_command(fb, args)
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    except FileBrowserError as e:
        print(json.dumps(
            _error(f"Command '{args.command}' failed: HTTP {e.status_code} — {str(e)}"),
            indent=2
        ))
        sys.exit(2)
    except Exception as e:
        print(json.dumps(
            _error(f"Command '{args.command}' error: {str(e)}"),
            indent=2
        ))
        sys.exit(2)


if __name__ == "__main__":
    main()
