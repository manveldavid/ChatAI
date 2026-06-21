---
name: filebrowser
description: Work with FileBrowser (https://filebrowser.org/) through its REST API. Use this skill whenever the user needs to interact with a FileBrowser server — downloading files, uploading files, managing files and folders (create, rename, move, copy, delete), creating public share links, managing users (list, create, delete), changing user passwords, checking server resources, or performing bulk file operations. Also use when the user mentions "filebrowser", "file browser server", or wants to manipulate files on a remote web file manager. Works with any FileBrowser instance via REST API — just provide base URL and login credentials.
---

# FileBrowser REST API

Skill for interacting with a [FileBrowser](https://filebrowser.org/) server programmatically via its REST API. Compatible with both standard FileBrowser v2 and FileBrowser Quantum v2.63+.

## What You Need From the User

1. **Server URL** (no trailing slash)
2. **Username**
3. **Password**
4. **Task**

## Using the Python Client

The skill includes a pre-built Python client at `references/filebrowser-client.py`
(`/app/agent/skills/filebrowser/references/filebrowser-client.py`).

Use `importlib.util` to dynamically load the client module into your code:

```python
import importlib.util
import sys

spec = importlib.util.spec_from_file_location(
    "filebrowser_client",
    "/app/agent/skills/filebrowser/references/filebrowser-client.py"
)
fb_mod = importlib.util.module_from_spec(spec)
sys.modules["filebrowser_client"] = fb_mod
spec.loader.exec_module(fb_mod)

fb = fb_mod.FileBrowser(
    "http://your-server:8080",  # ← your server URL
    "admin",                    # ← username
    "your-password"             # ← password
)

# fb is now authenticated — use any method below:
items = fb.list("/")
for item in items:
    print(item["name"], "→", "dir" if item["isDir"] else f'{item["size"]} bytes')
```

> **Important:** The token is obtained automatically during `__init__` — no manual login step needed.
> All methods raise `FileBrowserError(status_code, message)` on failure.

### Available Methods

| Category | Method | Description |
|----------|--------|-------------|
| **Directory** | `fb.list(path="/")` | List directory contents → `[{name, isDir, size, …}]` |
| | `fb.info(path)` | Get metadata for a single file/dir |
| | `fb.exists(path)` | Return True if path exists |
| | `fb.mkdirs(path)` | Create directory + parents |
| **Upload** | `fb.upload(local, remote, override=True)` | Upload local file to remote |
| | `fb.upload_string(content, remote, override=True)` | Upload string as a file |
| **Download** | `fb.download(remote, local)` | Download remote → save locally |
| | `fb.read_file(remote)` | Read remote file as bytes |
| | `fb.download_archive(paths, output_path)` | Download multiple as ZIP |
| **Mutate** | `fb.delete(path)` | Delete file or directory |
| | `fb.rename(source, dest)` | Rename/move |
| | `fb.move(source, dest)` | Alias for rename |
| | `fb.copy(source, dest)` | Copy file/dir |
| **Shares** | `fb.create_share(path, expire="")` | Create public share → `{hash, path, url}` |
| | `fb.list_shares()` | List all shares by current user |
| | `fb.delete_share(hash)` | Delete a share |
| **Users (admin)** | `fb.list_users()` | List all users |
| | `fb.create_user(username, password, scope, perm)` | Create a new user |
| | `fb.update_user(user_id, user_data)` | Update user (full object) |
| | `fb.change_user_password(user_id, password)` | Reset user password |
| | `fb.delete_user(user_id)` | Delete a user |
| **Server** | `fb.health_check()` | Server reachable? (no auth) |
| | `fb.server_info()` | Version & basic info |
| | `fb.server_settings()` | Full configuration |
| | `fb.search(query, path="/")` | Search files by name |
| | `fb.disk_usage(path="/")` | Returns `{"total", "used", "free"}` in bytes |
| **Sync & Diff** | `fb.diff(local, remote)` | Compare local ↔ remote → report |
| | `fb.sync_local_to_remote(local, remote, delete_extra, dry_run)` | Push local → cloud |
| | `fb.sync_remote_to_local(remote, local, delete_extra, dry_run)` | Pull cloud → local |
| **Low-level** | `fb.request(method, path, data, content_type)` | Raw HTTP → `(status, body_bytes)` |

## CLI Wrapper (run_skill_script)

For interactive use via `run_skill_script`, use the CLI wrapper at `scripts/filebrowser-cli.py`.
It dynamically loads the client (`../references/filebrowser-client.py`), logs in, and executes
the requested command — outputting **JSON** to stdout.

### Available CLI Commands

| Command | Arguments | Description |
|---------|-----------|-------------|
| `list` | `[path]` | List directory contents (default `/`) |
| `info` | `path` | Get metadata for a file/dir |
| `exists` | `path` | Check if path exists → `{"exists": true/false}` |
| `mkdirs` | `path` | Create directory + parents |
| `upload` | `local remote` | Upload local file to remote |
| `upload-string` | `content remote` | Upload a string as a file |
| `download` | `remote local` | Download remote file locally |
| `read-file` | `path` | Read remote file → `{"content_base64": "...", "size_bytes": N}` |
| `delete` | `path` | Delete file or directory |
| `rename` / `move` | `source destination` | Rename or move |
| `copy` | `source destination` | Copy file/dir |
| `create-share` | `path [--expire YYYY-MM-DD]` | Create public share link |
| `list-shares` | — | List all shares |
| `delete-share` | `hash` | Delete a share |
| `health-check` | — | Server reachable? → `{"healthy": true/false}` |
| `server-info` | — | Version and basic info |
| `server-settings` | — | Full server configuration |
| `disk-usage` | `[path]` | Disk usage → `{"total", "used", "free"}` |
| `search` | `query [--path /]` | Search files by name |
| `download-archive` | `paths... [--output LOCAL]` | Download as ZIP |
| `list-users` | — | List all users (admin) |
| `create-user` | `username password [scope]` | Create user (admin) |
| `delete-user` | `user_id` | Delete user (admin) |
| `change-password` | `user_id new_password` | Reset password (admin) |
| `diff` | `local_dir remote_dir` | Compare local vs remote |
| `sync-to-remote` | `local_dir remote_dir [--delete-extra] [--dry-run]` | Push local → cloud |
| `sync-from-remote` | `remote_dir local_dir [--delete-extra] [--dry-run]` | Pull cloud → local |




### Sync & Diff Details

- **`fb.diff(local, remote)`** — Returns report with `only_local`, `only_remote`, `only_local_dirs`, `only_remote_dirs`, `modified`, `identical`.
- **`fb.sync_local_to_remote(local, remote, delete_extra=False, dry_run=False)`** — Makes remote match local. Uploads new/changed files, creates dirs. If `delete_extra=True`, removes files on remote that don't exist locally.
- **`fb.sync_remote_to_local(remote, local, delete_extra=False, dry_run=False)`** — Makes local match remote. Downloads new/changed files, creates dirs. If `delete_extra=True`, removes local files not on remote.
- Both sync methods skip files that have identical size AND content hash. Pass `dry_run=True` to preview actions without modifying anything.

### ⚠️ Critical Gotchas

These are handled automatically by the client, but keep them in mind for custom `fb.request()` calls:

1. **Login returns plain text, NOT JSON** — the token is `response_text.strip()` (don't call `json.loads()`).
2. **Use `X-Auth` header, NOT `Authorization: Bearer`**.
3. **Creating directories requires a trailing slash** in the API path — without it, a FILE is created.
4. **Uploading sends raw bytes, NOT multipart/form-data** — using `files=` wraps data in MIME payload and corrupts the file.
5. **DELETE works for file/directory removal** — use `DELETE /api/resources/PATH` (not PATCH for delete).
6. **`/api/raw/` may return empty ZIP on some servers** — `download()` and `read_file()` auto-fallback to `/api/resources/{path}` content field.
7. **FileBrowser Quantum (v2.63+) endpoint differences:**
   - `server_info()`: reads from `/api/settings` (not `/api/server`)
   - `disk_usage()`: uses `GET /api/usage` → returns `{"total":N, "used":N}`
   - `search()`: uses `GET /api/search?query=...&path=...` → returns NDJSON
   - `rename()` / `copy()`: uses `PATCH /api/resources/{path}?action=...&destination=...`
   - `delete_share()`: uses `POST /api/shares?delete=true` with `{"hash":"..."}`
   - The client auto-detects and provides fallbacks for both versions.

### Path Conventions

- All paths are absolute, starting with `/`.
- URL-encode paths when used in query strings.
- For PATCH operations, paths in JSON body are sent raw (not URL-encoded).
- The API auto-normalizes double-slashes.
- `__pycache__` dirs are excluded from sync/diff operations.

## Reference Documents

- [FileBrowser Python Client](references/filebrowser-client.py) — pre-built REST API client (`FileBrowser` class)
- [Files API](references/files-api.md) — detailed endpoint reference for file/dir CRUD
- [Shares API](references/shares-api.md) — public share link management
- [Users API](references/users-api.md) — user administration (admin-only)
- [Resources API](references/resources-api.md) — health, settings, disk usage

<scripts>
  <script name="scripts/filebrowser-cli.py">
    <parameters_schema>Array of arguments passed to argparse (e.g. ["--url", "http://host:8080", "--user", "admin", "--pass", "pass", "list", "/"])</parameters_schema>
  </script>
  <script name="references/filebrowser-client.py">
    <parameters_schema>{"type":"array","items":{"type":"string"}}</parameters_schema>
  </script>
</scripts>
