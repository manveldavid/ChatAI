# Files API

## List Directory

```
GET /api/resources/PATH/
```

> **Important:** Trailing slash is recommended for directories. Without it, the behavior may differ (e.g. directory creation via POST will create a file instead).

Query param `type` to filter: `file`, `directory`, `media`.

Response includes `items` array with each item having: `name`, `size`, `type`, `modified`, `mode`.

For nested directories, use the `path` field of each item to construct the next request.

## Get File/Directory Info

```
GET /api/resources/PATH/FILENAME
```

Returns metadata for a single file/directory without downloading its content.

Check `isDir` in the response to distinguish files from directories.

## Read File Content

```
GET /api/files/raw/PATH/FILENAME
```

Returns raw file bytes. Use `download_file()` method on the client to save locally.

## Create Directory

```
POST /api/resources/PATH/NEWDIR/
```

> **⚠️ TRAILING SLASH IS REQUIRED!** If you omit the trailing slash, a FILE (not a directory) will be created.

No body required. The response is `200 OK`.

**Safe pattern:**
1. POST with trailing slash to create
2. GET to verify `isDir: true`
3. If `isDir: false`, DELETE and retry with trailing slash

## File Operations (PATCH)

```
PATCH /api/resources
Content-Type: application/json
```

Body template:
```json
{"what": "/destination", "which": ["/source"]}
```

| Action   | Body |
|----------|------|
| **Rename** | `{"what": "/parent/newname.txt", "which": ["/parent/oldname.txt"]}` |
| **Move**   | `{"what": "/new/dir/file.txt", "which": ["/old/dir/file.txt"]}` |
| **Copy**   | `{"what": "/dest/copy.txt", "which": ["/src/original.txt"]}` |
| **Delete** | `{"what": "", "which": ["/to/delete"]}` — supports multiple paths. |

> **Note:** Paths in the JSON body are **not** URL-encoded. Send them raw.
>
> ⚠️ PATCH delete may return 403 on some builds. Use `DELETE /api/resources/PATH` instead.

## Upload

```
POST /api/resources/PARENT_DIR/FILENAME?override=true
Content-Type: <appropriate MIME type>
```

> **See the Python client (`scripts/filebrowser.py`) for the correct upload implementation.**
> The client handles raw byte sending automatically — do NOT use `requests.post(..., files=...)`.

## Download Single File

```
GET /api/raw/?files=/PATH/FILE.TXT&token=TOKEN
```

The token is passed as a query string parameter — **no Bearer header needed**.
This produces a direct download link that works in any browser.
Do NOT use `/api/files/dl?files=...` — `/api/raw/?files=...` is the working endpoint.

## Delete

```
DELETE /api/resources/PATH
```

Works on both files and directories. Returns 204 on success.

> ⚠️ Prefer DELETE over PATCH for deletion — PATCH may return 403 on some builds.

## Bulk Download (zip)

```
POST /api/commands/dl
Content-Type: application/json
```

Body:
```json
{"files": ["/path/file1.txt", "/path/file2.txt"]}
```

Returns a JSON object with a temporary URL serving a `.zip` archive of all requested files.

> Note: This endpoint may not be available on all FileBrowser builds (returns 404).

## Search

```
POST /api/commands/search
Content-Type: application/json
```

Body:
```json
{"name": "search-term", "path": "/base/path"}
```

Returns an array of matching files and directories with full metadata.

> Note: This endpoint may not be available on all FileBrowser builds (returns 404).

## Gotchas

- **Login endpoint is `/api/login`** — NOT `/api/auth/login`. Returns plain text JWT token, NOT JSON.
- **Auth header is `X-Auth: {token}`** — NOT `Authorization: Bearer {token}`.
- **Download endpoint confusion:** The correct endpoint is `/api/raw/?files=...&token=...`, NOT `/api/files/dl?...`. This is a common mistake from outdated docs.
- **PATCH paths are not URL-encoded:** Send raw paths like `/my docs/file.txt` in the JSON body. The API handles normalization internally.
- **Directory creation:** `POST /api/resources/PATH/NEWDIR/` with **trailing slash** creates the directory. Without the slash, a FILE is created instead.
- **If you accidentally create a file instead of dir:** DELETE it first, then recreate with trailing slash.
- **Use `DELETE /api/resources/PATH` for deletion** — PATCH delete may return 403.
- **Upload to `/api/resources/PARENT/FILENAME`** — NOT `/api/files/PARENT`.

For Python code, use the `scripts/filebrowser.py` client which handles all these correctly by default.
