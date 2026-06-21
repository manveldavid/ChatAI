# Users API

> ⚠️ All user management operations require **admin** permissions.
> ⚠️ Auth header is `X-Auth: {token}` (NOT `Authorization: Bearer {token}`). Get the token via `POST /api/login`.

## List Users

```
GET /api/users
X-Auth: TOKEN
```

Returns an array of all user objects.

## Create User

```
POST /api/users
X-Auth: TOKEN
Content-Type: application/json
```

Body:
```json
{
  "username": "newuser",
  "password": "SecretPass123",
  "scope": "/",
  "locale": "en",
  "view_mode": "normal",
  "single_click": false,
  "perm": {
    "admin": false,
    "execute": false,
    "create": true,
    "read": true,
    "modify": false,
    "delete": false,
    "share": true,
    "rename": false,
    "move": false,
    "copy": false
  }
}
```

- `scope`: root directory the user can access (`/` for full access, `/uploads` to restrict).
- `perm`: granular permission object (see Permission Flags below).
- A user **cannot** access files outside their `scope`.

## Update User

```
PUT /api/users/ID
X-Auth: TOKEN
Content-Type: application/json
```

Send the **complete** updated user object. All fields must be present — partial updates are rejected.

A safe approach: `GET /api/users` first, modify the desired fields of the target user object, then `PUT` the whole object back.

## Change Password

```
PATCH /api/users/ID/password
X-Auth: TOKEN
Content-Type: application/json
```

Body:
```json
{"password": "NewPassword123"}
```

## Delete User

```
DELETE /api/users/ID
X-Auth: TOKEN
```

## Permission Flags

| Flag | Description |
|------|-------------|
| admin | Full admin panel access |
| create | Create files and directories |
| read | List directories and read files |
| modify | Edit / overwrite file contents |
| delete | Delete files and directories |
| share | Create public share links |
| rename | Rename files and directories |
| move | Move files between directories |
| copy | Copy files and directories |
| execute | Execute server commands |
