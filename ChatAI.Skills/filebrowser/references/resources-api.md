# Resources API

> ⚠️ Auth header is `X-Auth: {token}` (NOT `Authorization: Bearer {token}`). Get the token via `POST /api/login`.

Server configuration, health monitoring, and resource usage.

## Health Check

```
GET /api/healthcheck
```

No authentication needed. Returns `200 OK` with empty body if the server is running.

## Server Info (basic, no auth)

```
GET /api/server
```

Returns basic server information including version number.

## Server Settings (auth required)

```
GET /api/settings
X-Auth: TOKEN
```

Returns full server configuration including:
- Branding (name, disable external links)
- Server config (address, port, root path, TLS)
- Auth config (method, reCAPTCHA)
- Frontend settings (theme, color)
- User management flags
- TUS upload settings

## Disk Usage

```
POST /api/commands/du
X-Auth: TOKEN
Content-Type: application/json
```

Body:
```json
{"paths": ["/path/to/check"]}
```

Returns size in bytes for each requested path. Supports multiple paths in one call.

> Note: This endpoint may not be available on all FileBrowser builds (returns 404).
