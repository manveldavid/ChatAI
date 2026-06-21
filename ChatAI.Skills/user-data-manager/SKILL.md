---
name: user-data-manager
description: Secure personal data storage. Stores user profiles as markdown files in data/. Use when the user wants to: save personal data (FileBrowser server details, API keys, notes, any facts) that persists across conversations; retrieve their saved data in a new conversation by providing a username and PIN code; update their profile by adding, replacing, or removing data lines. Always trigger when the user asks to "remember" their information, mentions server/cloud details from a previous conversation, or requests to "log in" to stored data. If the user says "upload to my cloud", "connect to my server", or references previously saved details — load this skill first.
---

# User Data Manager

Stores user profiles as markdown files with PIN-based access.
All data stored in `data/` as `.md` files.

## Authentication

This skill delegates all PIN verification to the **authorize-user** skill.
Before any operation, authenticate via:

```bash
python ../authorize-user/scripts/verify.py <username> <pin>
```

All scripts in this skill automatically delegate to authorize-user for auth.
See **authorize-user** security rules for absolute restrictions.

## File Format

Each user has `data/<username>.md`:

```markdown
# User Profile: username

<!-- AUTH: pin_hash=<sha256> -->

## Данные
- filebrowser (url: http://example.com login: admin password: secret)
- username: Имя
- project: описание проекта

## Контекст и предпочтения
- Предпочитает ответы на русском языке
- Заметки о работе
```

### Обязательные элементы
- **AUTH line** (`<!-- AUTH: pin_hash=<sha256> -->`) — никогда не удалять и не изменять вручную.
- Никаких PIN, паролей, хэшей в теле файла — ЗАПРЕЩЕНО.

## Workflows

### 1. Login / Access data

Когда пользователь хочет получить доступ к своим данным:

```bash
python scripts/verify_pin.py <username> <pin>
```

Скрипт делегирует авторизацию в authorize-user, затем возвращает `md_content` профиля.

### 2. Registration

```bash
python scripts/register_user.py <username> <pin> '<json_array_of_data_lines>'
```

Скрипт сначала регистрирует пользователя через authorize-user, затем создаёт .md файл профиля.

### 3. Update Profile

```bash
python scripts/update_profile.py <username> <pin> <action> <search_or_line> [<new_line>]
```

| Action | Usage |
|--------|-------|
| add | `add "email: test@mail.com"` |
| replace | `replace "project" "project: новое значение"` |
| delete | `delete "notes"` |

### 4. Delete Profile

```bash
python scripts/delete_profile.py <username> <pin>
```

## Integration with FileBrowser

After successful verification:
1. Read `md_content`, find filebrowser credentials
2. Load **filebrowser** skill, authenticate, operate

---

<scripts>
  <script name="scripts/register_user.py">
    <parameters_schema>{"type":"array","items":{"type":"string"}}</parameters_schema>
  </script>
  <script name="scripts/delete_profile.py">
    <parameters_schema>{"type":"array","items":{"type":"string"}}</parameters_schema>
  </script>
  <script name="scripts/verify_pin.py">
    <parameters_schema>{"type":"array","items":{"type":"string"}}</parameters_schema>
  </script>
  <script name="scripts/update_profile.py">
    <parameters_schema>{"type":"array","items":{"type":"string"}}</parameters_schema>
  </script>
</scripts>
