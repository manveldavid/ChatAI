#!/usr/bin/env python3
"""filebrowser.py - sync client for the FileBrowser REST API.

Usage:
    import filebrowser
    fb = filebrowser.FileBrowser("http://host:8080", "admin", "password")

    # Directory operations
    fb.list("/")                          # list directory
    fb.info("/remote/file.txt")            # get file metadata
    fb.mkdirs("/remote/new-dir")           # creates parent dirs automatically

    # File operations
    fb.upload("/local/file.txt", "/remote/file.txt")
    fb.download("/remote/file.txt", "/local/download.txt")
    fb.read_file("/remote/cfg.json")       # read as bytes
    fb.upload_string("text", "/remote/t.txt")
    fb.delete("/remote/old.txt")
    fb.rename("/remote/old.txt", "/remote/new.txt")
    fb.move("/remote/file.txt", "/new/location/file.txt")
    fb.copy("/remote/file.txt", "/remote/copy.txt")

    # Shares
    fb.create_share("/remote/file.pdf")    # public share link
    fb.list_shares()
    fb.delete_share(hash_str)

    # Server operations
    fb.search("report.pdf", "/")
    fb.disk_usage("/")
    fb.health_check()                      # no auth needed

    # Low-level raw request
    code, body = fb.request("GET", "/api/resources/")
"""

import json
import mimetypes
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BSLASH = "\\"


class FileBrowserError(Exception):
    """Raised when a FileBrowser API call fails."""
    def __init__(self, status_code, message, body=b""):
        self.status_code = status_code
        self.body = body
        super().__init__(f"HTTP {status_code}: {message}")


class FileBrowser:
    """Simple synchronous client for the FileBrowser REST API."""

    # -- lifecycle --

    def __init__(self, server, username, password):
        self.server = server.rstrip("/")
        self._token = None
        self._login(username, password)

    # -- internal --

    def _login(self, username, password):
        """/api/login returns plain-text JWT (NOT JSON)."""
        req = urllib.request.Request(
            f"{self.server}/api/login",
            data=json.dumps({"username": username, "password": password}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                self._token = resp.read().decode().strip()
        except urllib.error.HTTPError as e:
            raise FileBrowserError(e.code, "Login failed", e.read())

    def request(self, method, path, data=None, content_type=None):
        """Authenticated request.  Returns (status_code, body_bytes).

        - dict/list data -> auto JSON-encoded (application/json).
        - str data -> UTF-8 encoded.
        - bytes data -> sent raw (use this for file uploads).
        - Auth via **X-Auth** header (NOT Authorization: Bearer).
        """
        url = f"{self.server}{path}"
        headers = {"X-Auth": self._token}

        if isinstance(data, (dict, list)):
            data = json.dumps(data).encode()
            headers["Content-Type"] = content_type or "application/json"
        elif isinstance(data, str):
            data = data.encode()
            if content_type:
                headers["Content-Type"] = content_type

        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.status, resp.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()

    def _request_json(self, method, path, data=None, content_type=None):
        """Return (status_code, parsed_json_or_string)."""
        code, body = self.request(method, path, data=data, content_type=content_type)
        try:
            parsed = json.loads(body) if body else {}
        except json.JSONDecodeError:
            parsed = {"_raw": body.decode(errors="replace")[:300]}
        return code, parsed

    # -- directory --

    def list(self, path="/"):
        """Return list of child items for *path*.
        Each item is a dict with keys: name, isDir, size, modified, path.
        Raises FileBrowserError(404) if path does not exist."""
        safe = path.rstrip("/") + "/"
        code, body = self.request("GET", f"/api/resources{safe}")
        if code == 404:
            raise FileBrowserError(code, f"Not found: {path}")
        if code != 200:
            raise FileBrowserError(code, body.decode(errors="replace")[:300])
        return json.loads(body).get("items", [])

    def info(self, path):
        """Get metadata for a single file or directory.
        Check result["isDir"] to distinguish directories from files."""
        code, body = self.request("GET", f"/api/resources{path}")
        if code == 404:
            raise FileBrowserError(code, f"Not found: {path}")
        if code != 200:
            raise FileBrowserError(code, body.decode(errors="replace")[:300])
        return json.loads(body)

    def exists(self, path):
        """Return True if a file or directory exists at *path*."""
        try:
            self.info(path)
            return True
        except FileBrowserError:
            return False

    def mkdirs(self, path):
        """Create a directory (and all parent directories) on the server.
        Trailing slash is sent in the API call -- required so the server
        creates a directory, not an empty file.
        """
        parts = Path(path.strip("/")).parts
        current = "/"
        for part in parts:
            current = current.rstrip("/") + "/" + part
            code, body = self.request("POST", f"/api/resources{current}/", data=b"")
            # 409 = already exists  (acceptable when walking parent chain)
            if code not in (200, 409):
                raise FileBrowserError(
                    code, f"mkdir {current}: {body.decode(errors='replace')[:200]}")

    # -- file transfer --

    def upload(self, local_path, remote_path, override=True):
        """Upload a local file to the remote server.
        Sends raw bytes (NOT multipart/form-data).  Using
        multipart/form-data corrupts the uploaded file.

        Args:
            local_path:  Path on the local filesystem.
            remote_path: Absolute path on the server (e.g. /uploads/data.csv).
            override:    Overwrite if the file already exists remotely.
        """
        with open(local_path, "rb") as f:
            content = f.read()
        mime, _ = mimetypes.guess_type(local_path)
        remote_path = remote_path.replace(BSLASH, "/")
        override_param = "?override=true" if override else ""
        code, body = self.request(
            "POST",
            f"/api/resources{remote_path}{override_param}",
            data=content,
            content_type=mime or "application/octet-stream",
        )
        if code not in (200, 201):
            raise FileBrowserError(
                code, f"Upload failed ({remote_path}): {body.decode(errors='replace')[:300]}")

    def download(self, remote_path, local_path):
        """Download a remote file to the local filesystem.
        
        Compatible with both standard FileBrowser v2 (/api/raw/) 
        and Quantum v2.63+ (/api/resources/ content field).
        Returns the local pathlib.Path object.
        """
        dest = Path(local_path)
        dest.parent.mkdir(parents=True, exist_ok=True)

        # Try /api/raw/ first
        encoded = urllib.parse.quote(remote_path.lstrip("/"))
        code, body = self.request("GET", f"/api/raw/?files={encoded}")
        if code == 200:
            # Reject empty ZIP
            if body[:2] != b"PK" or len(body) > 22:
                dest.write_bytes(body)
                return dest

        # Fallback: /api/resources content field
        code2, body2 = self.request("GET", f"/api/resources{remote_path}")
        if code2 in (200, 201):
            try:
                meta = json.loads(body2)
                content = meta.get("content")
                if content is not None:
                    dest.write_bytes(content.encode())
                    return dest
            except Exception:
                pass

        raise FileBrowserError(
            code, f"Download failed ({remote_path}): could not download file")


    def read_file(self, remote_path, use_content_if_text=False):
        """Return raw bytes of a remote file without saving locally.

        Automatically tries /api/resources/{path} content field first
        for text files, then falls back to /api/raw/ for binary content.
        Compatible with standard FileBrowser v2 and Quantum v2.63+.

        Args:
            remote_path: Absolute path on the server.
            use_content_if_text: Deprecated. If True, tries /api/resources
                content even for non-text files.
        """
        # Step 1: Check /api/resources for content field (text files)
        code, body = self.request("GET", f"/api/resources{remote_path}")
        if code in (200, 201):
            try:
                meta = json.loads(body)
                content = meta.get("content")
                file_type = meta.get("type", "")
                is_text = file_type == "text" or use_content_if_text
                if content is not None and is_text:
                    return content.encode()
            except Exception:
                pass  # fallthrough to binary download

        # Step 2: /api/raw/ for binary files
        encoded = urllib.parse.quote(remote_path.lstrip("/"))
        code, body = self.request("GET", f"/api/raw/?files={encoded}")
        if code == 200:
            # Reject empty ZIP
            if body[:2] != b"PK" or len(body) > 22:
                return body

        # Step 3: Fallback — try /api/resources content regardless of type
        code2, body2 = self.request("GET", f"/api/resources{remote_path}")
        if code2 in (200, 201):
            try:
                meta = json.loads(body2)
                content = meta.get("content")
                if content is not None:
                    return content.encode()
            except Exception:
                pass

        raise FileBrowserError(
            code, f"Read failed ({remote_path}): could not read file content")

    def upload_string(self, content, remote_path, override=True):
        """Upload a string as a file (useful for quick text / JSON config)."""
        suffix = "?override=true" if override else ""
        code, body = self.request(
            "POST", f"/api/resources{remote_path}{suffix}",
            data=content.encode())
        if code not in (200, 201):
            raise FileBrowserError(
                code, f"Upload failed ({remote_path}): {body.decode(errors='replace')[:300]}")

    # -- mutating operations --

    def delete(self, path):
        """Delete a file or directory.  Uses DELETE (preferred over PATCH)."""
        code, body = self.request("DELETE", f"/api/resources{path}")
        if code not in (200, 204):
            raise FileBrowserError(
                code, f"Delete failed ({path}): {body.decode(errors='replace')[:300]}")

    def rename(self, source, destination):
        """Rename or move a file/directory.
        
        Compatible with both standard FileBrowser v2 (PATCH /api/resources)
        and Quantum v2.63+ (PATCH /api/resource/{path}?action=rename&destination=...).
        """
        # Quantum-style: PATCH on the resource with action+destination params
        enc_dest = urllib.parse.quote(destination)
        code, body = self.request(
            "PATCH", f"/api/resources{source}?action=rename&destination={enc_dest}",
            data=b"")
        if code in (200, 204):
            return

        # Fallback: standard v2 PATCH
        code2, body2 = self.request(
            "PATCH", "/api/resources/",
            data=json.dumps({"what": destination, "which": [source]}),
            content_type="application/json")
        if code2 in (200, 204):
            return

        raise FileBrowserError(
            code, f"Rename failed: {body.decode(errors='replace')[:300]}")

    def move(self, source, destination):
        """Move a file or directory to a new location."""
        self.rename(source, destination)

    def copy(self, source, destination):
        """Copy a file or directory.
        
        Compatible with both standard FileBrowser v2 and Quantum v2.63+.
        """
        # Quantum-style
        enc_dest = urllib.parse.quote(destination)
        code, body = self.request(
            "PATCH", f"/api/resources{source}?action=copy&destination={enc_dest}",
            data=b"")
        if code in (200, 204):
            return

        # Fallback: standard v2
        code2, body2 = self.request(
            "PATCH", "/api/resources/",
            data=json.dumps({"what": destination, "which": [source], "action": "copy"}),
            content_type="application/json")
        if code2 in (200, 204):
            return

        raise FileBrowserError(
            code, f"Copy failed: {body.decode(errors='replace')[:300]}")

    # -- shares --

    def create_share(self, path, expire=""):
        """Create a public share link.
        Returns a dict with hash, path, and url."""
        code, result = self._request_json(
            "POST", "/api/shares",
            data={"path": path, "expire": expire})
        if code not in (200, 201):
            raise FileBrowserError(code, f"Create share failed: {result}")
        if isinstance(result, dict):
            return {
                "hash": result.get("hash", "unknown"),
                "path": result.get("path", path),
                "url": f"{self.server}/public/share/{result.get('hash', '')}",
            }
        return {"hash": str(result), "path": path}

    def list_shares(self):
        """Return a list of all shares created by the current user."""
        code, body = self.request("GET", "/api/shares")
        if code not in (200, 201):
            raise FileBrowserError(code, body.decode(errors="replace")[:300])
        return json.loads(body)

    def delete_share(self, share_hash):
        """Delete a public share by its hash.
        
        Compatible with both standard FileBrowser v2 (DELETE)
        and Quantum v2.63+ (POST /api/shares?delete=true).
        """
        # Quantum-style
        code, body = self.request(
            "POST", "/api/shares?delete=true",
            data=json.dumps({"hash": share_hash}),
            content_type="application/json")
        if code in (200, 204):
            return

        # Fallback: standard v2 DELETE
        code2, body2 = self.request("DELETE", f"/api/shares/{share_hash}")
        if code2 in (200, 204):
            return

        raise FileBrowserError(
            code, f"Delete share failed: {body.decode(errors='replace')[:300]}")

    # -- server operations --

    def health_check(self):
        """Return True if the server is reachable (no auth needed)."""
        req = urllib.request.Request(f"{self.server}/api/healthcheck")
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status == 200
        except Exception:
            return False

    def search(self, query, path="/"):
        """Search for files by name.
        
        Compatible with both standard FileBrowser v2 and Quantum v2.63+.
        Returns a list of dicts with {"name", "path", "size", "isDir"}.
        """
        # Quantum: GET /api/search?query=...&path=... (returns NDJSON)
        eq = urllib.parse.quote(query)
        ep = urllib.parse.quote(path)
        code, body = self.request("GET", f"/api/search?query={eq}&path={ep}")
        if code == 200:
            results = []
            for line in body.decode(errors="replace").split("\n"):
                line = line.strip()
                if not line:
                    continue
                try:
                    results.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
            return results

        # Fallback: POST /api/commands/search
        code2, parsed = self._request_json(
            "POST", "/api/commands/search",
            data={"name": query, "path": path})
        if code2 in (200, 201):
            if isinstance(parsed, list):
                return parsed
            return parsed.get("data", [])

        return []  # Endpoint unavailable

    def disk_usage(self, path="/"):
        """Return disk usage dict with total, used, and free bytes.
        
        Compatible with both standard FileBrowser v2 and Quantum v2.63+.
        Returns {"total": N, "used": N, "free": N}.
        """
        # Quantum: GET /api/usage
        code, body = self.request("GET", "/api/usage")
        if code == 200:
            data = json.loads(body)
            total = data.get("total", 0)
            used = data.get("used", 0)
            return {"total": total, "used": used, "free": total - used}

        # Fallback: list dir and sum
        safe = path.rstrip("/") + "/" if path != "/" else "/"
        code2, body2 = self.request("GET", f"/api/resources{safe}")
        if code2 == 200:
            data = json.loads(body2)
            total_size = sum(i.get("size", 0) for i in data.get("items", []))
            return {"used": total_size}

        return {"total": 0, "used": 0, "free": 0}

    # -- user management (admin only) --

    def list_users(self):
        """Return a list of all users.  Requires admin privileges."""
        code, body = self.request("GET", "/api/users")
        if code not in (200, 201):
            raise FileBrowserError(
                code, f"List users failed: {body.decode(errors='replace')[:300]}")
        return json.loads(body)

    def create_user(self, username, password, scope="/", perm=None,
                    locale="en", view_mode="normal", single_click=False):
        """Create a new user.  Requires admin privileges.

        Args:
            username:   Login name.
            password:   Initial password.
            scope:      Root directory the user can access (default "/").
            perm:       Optional dict of permission booleans.  Defaults
                        to read + create + share.
            locale:     UI locale (default "en").
            view_mode:  "normal" or "compact".
            single_click: Whether single-click opens files.

        Returns:
            The created user dict as returned by the API.
        """
        if perm is None:
            perm = self._default_perm()

        payload = {
            "username": username,
            "password": password,
            "scope": scope,
            "locale": locale,
            "view_mode": view_mode,
            "single_click": single_click,
            "perm": perm,
        }
        code, body = self.request("POST", "/api/users", data=payload)
        if code not in (200, 201):
            raise FileBrowserError(
                code, f"Create user failed: {body.decode(errors='replace')[:300]}")
        return json.loads(body)

    def update_user(self, user_id, user_data):
        """Update an existing user.  Requires admin privileges.

        The API expects the *complete* user object — partial updates are
        rejected.  The safe pattern: `GET /api/users` first, mutate the
        entry you want to change, then `PUT` it back.

        Args:
            user_id:    Numeric user ID (from list_users).
            user_data:  Full user dict (must include all fields).

        Returns:
            The updated user dict.
        """
        # Build the payload — the FileBrowser PUT wrapper needs this shape
        payload = {
            "what": "user",
            "which": [],
            "data": user_data,
        }
        code, body = self.request("PUT", f"/api/users/{user_id}", data=payload)
        if code not in (200, 201, 204):
            raise FileBrowserError(
                code, f"Update user failed: {body.decode(errors='replace')[:300]}")
        if body:
            return json.loads(body)
        return user_data

    def change_user_password(self, user_id, new_password):
        """Reset a user's password.  Requires admin privileges."""
        code, body = self.request(
            "PATCH", f"/api/users/{user_id}/password",
            data={"password": new_password})
        if code not in (200, 201, 204):
            raise FileBrowserError(
                code, f"Change password failed: {body.decode(errors='replace')[:300]}")

    def delete_user(self, user_id):
        """Delete a user by ID.  Requires admin privileges."""
        code, body = self.request("DELETE", f"/api/users/{user_id}")
        if code not in (200, 204):
            raise FileBrowserError(
                code, f"Delete user failed: {body.decode(errors='replace')[:300]}")

    @staticmethod
    def _default_perm():
        return {
            "admin": False,
            "execute": False,
            "create": True,
            "read": True,
            "modify": False,
            "delete": False,
            "share": True,
            "rename": False,
            "move": False,
            "copy": False,
        }

    # -- server config --

    def server_info(self):
        """Return basic server info (version, auth method, …).
        
        Compatible with both standard FileBrowser v2 and Quantum v2.63+.
        Returns a dict with version, authMethod, signup, and full settings.
        """
        code, body = self.request("GET", "/api/settings")
        if code == 200:
            data = json.loads(body)
            branding = data.get("branding", {})
            return {
                "version": branding.get("name", "FileBrowser Quantum"),
                "authMethod": data.get("authMethod", "json"),
                "signup": data.get("signup", False),
                "settings": data,
            }
        # Fallback for older versions
        code2, body2 = self.request("GET", "/api/server")
        if code2 == 200:
            return json.loads(body2)
        raise FileBrowserError(
            code, f"Server info failed: {body.decode(errors='replace')[:300]}")

    def server_settings(self):
        """Return full server configuration (branding, auth, theme, …).
        Requires authentication."""
        code, body = self.request("GET", "/api/settings")
        if code != 200:
            raise FileBrowserError(
                code, f"Server settings failed: {body.decode(errors='replace')[:300]}")
        return json.loads(body)

    # -- bulk download --

    def download_archive(self, paths, output_path=None):
        """Download multiple files/directories as a ZIP archive.

        Args:
            paths:        List of absolute remote paths.
            output_path:  Local path to save the ZIP.  If None, returns
                          raw bytes.

        Returns:
            pathlib.Path to the saved file, or raw bytes if output_path
            is None.
        """
        code, body = self.request(
            "POST", "/api/commands/dl",
            data={"files": paths})
        if code not in (200, 201):
            raise FileBrowserError(
                code, f"Download archive failed: {body.decode(errors='replace')[:300]}")
        parsed = json.loads(body)
        # The command/dl endpoint returns a JSON object with a temp URL:
        # {"url": "https://.../download/archive.zip?token=..."}
        url = parsed.get("url") or parsed.get("URL")
        if url:
            # Download from the presigned URL
            req = urllib.request.Request(url)
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    archive = resp.read()
            except urllib.error.HTTPError as e:
                raise FileBrowserError(e.code, f"Archive download failed", e.read())
        else:
            # Fallback — raw response *is* the archive
            archive = body

        if output_path:
            dest = Path(output_path)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(archive)
            return dest
        return archive


    # -- synchronization & diff --

    def _build_file_tree_remote(self, remote_path, prefix=""):
        """Recursively build a file tree dict for a remote directory.
        Returns: {relative_path: {"isDir": bool, "size": int, "modified": str}}
        """
        tree = {}
        try:
            items = self.list(remote_path)
        except Exception:
            return tree
        for item in items:
            name = item["name"]
            rel = prefix + "/" + name if prefix else name
            isDir = item.get("isDir", False)
            entry = {"isDir": isDir, "size": item.get("size", 0), "modified": item.get("modified", "")}
            tree[rel] = entry
            if isDir:
                sub = self._build_file_tree_remote(remote_path.rstrip("/") + "/" + name, prefix=rel)
                tree.update(sub)
        return tree

    def _build_file_tree_local(self, local_path):
        """Recursively build a file tree dict for a local directory.
        Returns: {relative_path: {"isDir": bool, "size": int}}
        """
        import os as _os
        tree = {}
        local_path = local_path.rstrip("/")
        for root, dirs, files in _os.walk(local_path):
            # Skip __pycache__ and hidden dirs
            dirs[:] = [d for d in dirs if d != "__pycache__" and not d.startswith(".")]
            rel_root = _os.path.relpath(root, local_path)
            if rel_root != ".":
                tree[rel_root] = {"isDir": True, "size": 0}
            for f in files:
                if f.startswith(".") or f == "__pycache__":
                    continue
                full = _os.path.join(root, f)
                rel = _os.path.join(rel_root, f) if rel_root != "." else f
                rel = rel.replace("\\", "/")  # Normalize separators
                tree[rel] = {"isDir": False, "size": _os.path.getsize(full)}
        return tree

    def diff(self, local_path, remote_path):
        """Compare a local directory with a remote directory.
        Returns a dict with keys:
          only_local: set of relative paths only in local
          only_remote: set of relative paths only in remote
          modified: dict of rel_path -> {"local_size": int, "remote_size": int}
          identical: set of rel_paths that match by size (for text files)
        """
        import os as _os
        import hashlib as _hashlib

        local_tree = self._build_file_tree_local(local_path)
        remote_tree = self._build_file_tree_remote(remote_path)

        local_files = {k: v for k, v in local_tree.items() if not v["isDir"]}
        remote_files = {k: v for k, v in remote_tree.items() if not v["isDir"]}

        local_dirs = {k for k, v in local_tree.items() if v["isDir"]}
        remote_dirs = {k for k, v in remote_tree.items() if v["isDir"]}

        only_local = set(local_files.keys()) - set(remote_files.keys())
        only_remote = set(remote_files.keys()) - set(local_files.keys())

        modified = {}
        identical = set()

        common = set(local_files.keys()) & set(remote_files.keys())
        for rel in sorted(common):
            ls = local_files[rel]["size"]
            rs = remote_files[rel]["size"]
            if ls != rs:
                modified[rel] = {"local_size": ls, "remote_size": rs}
            else:
                # Same size - check content hash for text files
                # Read remote content
                code, body = self.request("GET", f"/api/resources{remote_path.rstrip('/')}/{rel}")
                if code in (200, 201) and body:
                    try:
                        meta = json.loads(body)
                        remote_content = meta.get("content", "")
                        if remote_content:
                            # Hash remote content
                            remote_hash = _hashlib.md5(remote_content.encode()).hexdigest()
                            # Hash local file
                            local_hash = _hashlib.md5(open(_os.path.join(local_path, rel), 'rb').read()).hexdigest()
                            if remote_hash == local_hash:
                                identical.add(rel)
                            else:
                                modified[rel] = {"local_size": ls, "remote_size": rs, "content_differs": True}
                        else:
                            # Binary file - size match suggests identical
                            identical.add(rel)
                    except Exception:
                        identical.add(rel)  # Assume identical if can't check
                else:
                    identical.add(rel)

        # Check dirs
        only_local_dirs = local_dirs - remote_dirs
        only_remote_dirs = remote_dirs - local_dirs

        return {
            "only_local": sorted(only_local),
            "only_remote": sorted(only_remote),
            "only_local_dirs": sorted(only_local_dirs),
            "only_remote_dirs": sorted(only_remote_dirs),
            "modified": modified,
            "identical": sorted(identical),
        }

    def sync_local_to_remote(self, local_path, remote_path, delete_extra=False, dry_run=False):
        """Synchronize local directory to remote.
        Makes remote identical to local.
        upload files, create dirs, optionally delete extra remote files.
        """
        import os as _os
        report = {"uploaded": [], "created_dirs": [], "deleted": [], "skipped": []}

        local_tree = self._build_file_tree_local(local_path)
        remote_tree = self._build_file_tree_remote(remote_path)

        local_files = {k: v for k, v in local_tree.items() if not v["isDir"]}
        remote_files = {k: v for k, v in remote_tree.items() if not v["isDir"]}

        local_dirs = {k for k, v in local_tree.items() if v["isDir"]}
        remote_dirs = {k for k, v in remote_tree.items() if v["isDir"]}

        # Create dirs that exist locally but not remotely
        dirs_to_create = sorted(local_dirs - remote_dirs)
        for d in dirs_to_create:
            full_remote = f"{remote_path.rstrip('/')}/{d}"
            if dry_run:
                report["created_dirs"].append(f"[DRY RUN] {full_remote}")
            else:
                self.mkdirs(full_remote)
                report["created_dirs"].append(full_remote)

        # Upload/overwrite files
        for rel, info in sorted(local_files.items()):
            local_file = _os.path.join(local_path, rel)
            # Check if file exists remotely with same size
            if rel in remote_files:
                remote_size = remote_files[rel]["size"]
                if remote_size == info["size"] and not dry_run:
                    # Same size - check content
                    code, body = self.request("GET", f"/api/resources{remote_path.rstrip('/')}/{rel}")
                    if code in (200, 201) and body:
                        try:
                            import hashlib
                            meta = json.loads(body)
                            rc = meta.get("content", "")
                            if rc:
                                rh = hashlib.md5(rc.encode()).hexdigest()
                                lh = hashlib.md5(open(local_file, 'rb').read()).hexdigest()
                                if rh == lh:
                                    report["skipped"].append(rel)
                                    continue
                        except Exception:
                            report["skipped"].append(rel)
                            continue

            full_remote = f"{remote_path.rstrip('/')}/{rel}"
            if dry_run:
                report["uploaded"].append(f"[DRY RUN] {local_file} -> {full_remote}")
            else:
                self.upload(local_file, full_remote, override=True)
                report["uploaded"].append(f"{local_file} -> {full_remote}")

        # Delete extra remote files/dirs
        if delete_extra:
            extra_remote_files = set(remote_files.keys()) - set(local_files.keys())
            extra_remote_dirs = remote_dirs - local_dirs

            for d in sorted(extra_remote_dirs, reverse=True):  # Delete deepest first
                full_remote = f"{remote_path.rstrip('/')}/{d}"
                if dry_run:
                    report["deleted"].append(f"[DRY RUN] Dir: {full_remote}")
                else:
                    self.delete(full_remote)
                    report["deleted"].append(f"Dir: {full_remote}")

            for f in sorted(extra_remote_files):
                full_remote = f"{remote_path.rstrip('/')}/{f}"
                if dry_run:
                    report["deleted"].append(f"[DRY RUN] {full_remote}")
                else:
                    self.delete(full_remote)
                    report["deleted"].append(full_remote)

        return report

    def sync_remote_to_local(self, remote_path, local_path, delete_extra=False, dry_run=False):
        """Synchronize remote directory to local.
        Makes local identical to remote.
        """
        import os as _os
        report = {"downloaded": [], "created_dirs": [], "deleted": [], "skipped": []}

        local_tree = self._build_file_tree_local(local_path)
        remote_tree = self._build_file_tree_remote(remote_path)

        local_files = {k: v for k, v in local_tree.items() if not v["isDir"]}
        remote_files = {k: v for k, v in remote_tree.items() if not v["isDir"]}

        local_dirs = {k for k, v in local_tree.items() if v["isDir"]}
        remote_dirs = {k for k, v in remote_tree.items() if v["isDir"]}

        # Create dirs that exist remotely but not locally
        for d in sorted(remote_dirs - local_dirs):
            full_local = _os.path.join(local_path, d)
            if dry_run:
                report["created_dirs"].append(f"[DRY RUN] {full_local}")
            else:
                _os.makedirs(full_local, exist_ok=True)
                report["created_dirs"].append(full_local)

        # Download files
        for rel, info in sorted(remote_files.items()):
            local_file = _os.path.join(local_path, rel)
            if rel in local_files and local_files[rel]["size"] == info["size"]:
                # Same size - try content check for text
                try:
                    code, body = self.request("GET", f"/api/resources{remote_path.rstrip('/')}/{rel}")
                    if code in (200, 201) and body:
                        import hashlib
                        meta = json.loads(body)
                        rc = meta.get("content", "")
                        if rc:
                            rh = hashlib.md5(rc.encode()).hexdigest()
                            lh = hashlib.md5(open(local_file, 'rb').read()).hexdigest()
                            if rh == lh:
                                report["skipped"].append(rel)
                                continue
                except Exception:
                    report["skipped"].append(rel)
                    continue

            full_remote = f"{remote_path.rstrip('/')}/{rel}"
            if dry_run:
                report["downloaded"].append(f"[DRY RUN] {full_remote} -> {local_file}")
            else:
                self.download(full_remote, local_file)
                report["downloaded"].append(f"{full_remote} -> {local_file}")

        # Delete extra local files/dirs
        if delete_extra:
            extra_local_files = set(local_files.keys()) - set(remote_files.keys())
            extra_local_dirs = local_dirs - remote_dirs

            for f in sorted(extra_local_files):
                full_local = _os.path.join(local_path, f)
                if dry_run:
                    report["deleted"].append(f"[DRY RUN] {full_local}")
                else:
                    _os.remove(full_local)
                    report["deleted"].append(full_local)

            for d in sorted(extra_local_dirs, reverse=True):
                full_local = _os.path.join(local_path, d)
                if dry_run:
                    report["deleted"].append(f"[DRY RUN] Dir: {full_local}")
                else:
                    import shutil
                    shutil.rmtree(full_local)
                    report["deleted"].append(f"Dir: {full_local}")

        return report

    # -- repr --

    def __repr__(self):
        t = self._token[-6:] if self._token else "None"
        return f"FileBrowser({self.server!r}, token=...{t})"


if __name__ == "__main__":
    print(__doc__)
