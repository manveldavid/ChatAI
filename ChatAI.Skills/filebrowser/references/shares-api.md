# Shares API

> ⚠️ Auth header is `X-Auth: {token}` (NOT `Authorization: Bearer {token}`). Get the token via `POST /api/login`.

Create public download links that do not require authentication to access.

## List Shares

```
GET /api/shares
X-Auth: TOKEN
```

Returns all shares created by the current user. Each share object contains:
`id`, `hash`, `path`, `expire`, `user_id`, `username`.

## Create Share

```
POST /api/shares
X-Auth: TOKEN
Content-Type: application/json
```

Body:
```json
{"path": "/path/to/file.pdf", "expire": ""}
```

- `path` (required): absolute file or directory path on the server.
- `expire` (optional): ISO 8601 date/time, or empty string for no expiration.

## Delete Share

```
DELETE /api/shares/HASH
X-Auth: TOKEN
```

## Accessing a Share

Public URL format:
```
{SERVER_URL}/share/{HASH}
```

- For **single files**: the download starts immediately in the browser.
- For **directories**: users see a web interface to browse and select files to download.

> Shares are public — anyone with the URL can access them. No login required.
