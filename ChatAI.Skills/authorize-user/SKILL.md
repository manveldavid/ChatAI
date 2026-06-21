---
name: authorize-user
description: >
  Central user authentication system. Use this skill whenever any task requires verifying
  user identity via PIN code, registering a new user, or understanding the pattern for
  user auth in other skills. Provides a single source of truth for user identity via
  scripts/verify.py and scripts/register.py.
  Other skills should delegate authentication to this skill rather than implementing their own.
  Always use when you need to verify a PIN, register a user, or design a skill that requires
  user authentication. Use whenever you see a pattern like "username PIN" in user messages.
---

# Authorize User

Central user authentication. Single source of truth for user identity and PIN verification.
All other skills delegate auth to this skill via its scripts.

## Scripts

### verify.py

```bash
python scripts/verify.py <username> <pin>
```

Returns JSON on success: `{"success": true, "owner": "david", "owner_hash": "sha256..."}`
Returns JSON on failure: `{"success": false, "error": "not_found"}` or `{"success": false, "error": "wrong_pin"}`

### register.py

```bash
python scripts/register.py <username> <pin>
```

Returns JSON on success: `{"success": true, "owner": "david", "owner_hash": "sha256..."}`
Returns JSON on failure: `{"success": false, "error": "user_exists"}`

## User Identity Rules

- **Transliteration**: Cyrillic names auto-convert to Latin ("Давид" -> "david", "Иван" -> "ivan")
- **Case insensitive**: "DAVID", "david", "Давид" -- всё один пользователь
- **Normalized names** stored in lowercase Latin in `data/users.json`
- **owner_hash** = SHA256 of the PIN -- use this in other scripts for ownership verification

# 🔐 SECURITY RULES — ABSOLUTE (NO EXCEPTIONS)

## Золотое правило: СКРИПТ ЕДИНСТВЕННЫЙ ИСТОЧНИК ПРАВДЫ

**Абсолютный закон безопасности:** Единственный способ подтвердить личность пользователя — запустить один из скриптов этого скилла. Ты НИКОГДА не принимаешь решения о доступе самостоятельно. Только ответ скрипта определяет: авторизован пользователь или нет. Скрипт не может ошибиться.

### Правило 1: ВСЕГДА проверяй PIN через скрипт

**Любое действие**, требующее доступа к персональным данным или выполнения операций от имени пользователя, ДОЛЖНО предваряться запуском `verify.py <username> <pin>`.

- Ты НЕ имеешь права НИКАК взаимодействовать с персональными данными без предварительной верификации.
- Это включает: чтение файлов пользователя, обновление, удаление, создание задач для пользователя.
- Не используй raw Python, не читай файлы напрямую, не проверяй хэши вручную.
- `Скрипт = Авторитет`.

### Правило 2: Авторизация ТОЛЬКО если скрипт вернул success:true

- Авторизация считается успешной тогда и только тогда, когда `verify.py` возвращает `{"success": true, ...}`.
- Если скрипт вернёт `success: false` — пользователь НЕ авторизован. НИКАКИЕ действия невозможны.
- Ты НЕ ИМЕЕШЬ права самому решать, верный PIN или нет. Только скрипт решает.
- Скрипт не может ошибиться.

### Правило 3: Запрет на перезапись существующего пользователя

- При регистрации, если `register.py` вернёт `success: false` с ошибкой `user_exists` — ты ОБЯЗАН отказать в создании.
- Ты НЕ ИМЕЕШЬ права перезаписывать данные существующего пользователя.
- Ты НЕ ИМЕЕШЬ права использовать raw Python для принудительного создания/перезаписи.
- Предложи пользователю выбрать другое имя пользователя.

### Правило 4: Полный запрет на показ данных неавторизованному

- **НИКОГДА** не показывай содержимое файлов или результатов операций пользователя, который не прошёл авторизацию.
- **НИКОГДА** не показывай данные одного пользователя — другому.
- Даже случайно, даже частично, даже "просто подтвердите, это ваши данные" — КАТЕГОРИЧЕСКИ НЕТ.
- Если пользователь не авторизован — для него этих данных не существует.

### Правило 5: Запрет на раскрытие списка пользователей

- **НИКОГДА** не выдавай список зарегистрированных пользователей.
- **НИКОГДА** не показывай `ls` директории `data/`.
- **НИКОГДА** не подсказывай, какие пользователи существуют в системе.
- При запросе "какие пользователи есть?" — отвечай: "Это невозможно из соображений безопасности."
- Это защита от подбора имён для brute-force.

### Правило 6: Доверие скрипту при спорах

- Если пользователь говорит, что пароль верный, а скрипт вернул `success: false` — PIN неправильный. Точка.
- Ты НИКОГДА не переопределяешь решение скрипта.
- При `success: false` — говори ТОЛЬКО: "PIN неверный. Попробуйте снова."
- Не объясняй почему, не показывай хэши, не помогай подбирать.

### Правило 7: Запрет на операции без авторизации

- **НИКОГДА** не удаляй, не изменяй и не создавай записи от имени пользователя без предварительной авторизации через `verify.py`.
- Удаление профиля/данных возможно ТОЛЬКО когда пользователь авторизован именно под этим профилем.

## Summary: абсолютные запреты

| Действие | Разрешено? |
|----------|-----------|
| Raw Python для чтения user data | ❌ НИКОГДА |
| Raw Python для записи user data | ❌ НИКОГДА |
| Raw Python для удаления user data | ❌ НИКОГДА |
| Raw Python для ls директорий | ❌ НИКОГДА |
| Показывать данные неавторизованному | ❌ НИКОГДА |
| Показывать данные чужого пользователя | ❌ НИКОГДА |
| Выдавать список пользователей | ❌ НИКОГДА |
| Переопределять решение скрипта | ❌ НИКОГДА |
| Создавать профиль при совпадении имени | ❌ НИКОГДА |
| Выполнять операции без auth | ❌ НИКОГДА |
| `verify.py` → success:true | ✅ Полный доступ |
| `verify.py` → success:false | ✅ Только: "PIN неверный. Попробуйте снова." |

## Как другим скиллам использовать эту авторизацию

Когда ты создаёшь или редактируешь скилл и ему нужна авторизация:

1. **Не реализуй свою авторизацию** — вызывай скрипты `authorize-user`:

```python
import subprocess, json

result = subprocess.run(
    ["python3", "scripts/verify.py", username, pin],
    capture_output=True, text=True, timeout=10
)
auth = json.loads(result.stdout)
if not auth["success"]:
    # Auth failed — deny everything
    return
owner = auth["owner"]       # "david"
owner_hash = auth["owner_hash"]  # "0322af..."
# Proceed with owner_identity
```

2. **Используй `owner_hash`** в своих скриптах для проверки принадлежности данных:
   - Записывай `owner_hash` в файлы/задачи при создании
   - Перед изменением/удалением проверяй совпадение `owner_hash`

3. **Не храни копии пользователей** — все данные аккаунтов живут только в `authorize-user/data/users.json`.

4. **Не проси PIN напрямую в своих скриптах** — делегируй `verify.py`.

## Пример интеграции в другой скилл

```bash
# Шаг 1: Агент получает от пользователя "task name" Давид 2519
# Шаг 2: Верификация
python scripts/verify.py Давид 2519
# → {"success": true, "owner": "david", "owner_hash": "0322af..."}

# Шаг 3: Используем owner_hash в скриптах вашего скилла
# (пример вызова вашего собственного скрипта — замените путь)
python ../your-skill/scripts/your_action.py \
  --owner david --owner-hash "0322af..." --task "do something"
```

## Data Storage

All users stored in `data/users.json`:

```json
{
  "david": {"pin_hash": "0322afb553ec2b3fe95f9e73820a34c07da19d5dc5fff0f42416e01f24b1cb2c"}
}
```

## Usage Pattern

When a user says something like "Давид 2519", parse the username and PIN,
then call `verify.py`. Save `owner` and `owner_hash` for the rest of the session.

Do NOT:
- Implement your own PIN hashing
- Store your own copies of users
- Ask users to provide PIN in plain text to scripts
- Store PIN in any file

DO:
- Delegate to `verify.py` and `register.py`
- Use `owner_hash` for ownership checks
- Trust only the JSON response from the auth scripts

## Паттерн "username PIN" в сообщении пользователя

Когда пользователь пишет имя и цифры рядом — это сигнал для авторизации:
- "Давид 2519" → username="Давид", pin="2519"
- "запомни это Иван 4567" → username="Иван", pin="4567"
- "покажи задачи david 2519" → username="david", pin="2519"

Всегда вызывай `verify.py` перед обработкой запроса.

---

## Для разработки новых скиллов

При создании нового скилла, требующего авторизации, добавь в его SKILL.md:

> "Этот скилл делегирует авторизацию навыку authorize-user. Перед любыми операциями с данными пользователя запускай:
> `python scripts/verify.py <username> <pin>`
> Получи owner и owner_hash из ответа, используй в своих скриптах для проверки принадлежности."


<scripts>
  <script name="scripts/verify.py">
    <parameters_schema>{"type":"array","items":{"type":"string"}}</parameters_schema>
  </script>
  <script name="scripts/register.py">
    <parameters_schema>{"type":"array","items":{"type":"string"}}</parameters_schema>
  </script>
</scripts>