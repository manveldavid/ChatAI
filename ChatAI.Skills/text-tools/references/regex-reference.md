# Regular Expressions Reference

Quick reference for regex patterns used in text search and replace operations.

## Basic Patterns

| Pattern | Description | Example |
|---------|-------------|---------|
| `.` | Any character (except newline) | `a.c` matches "abc", "axc" |
| `\d` | Digit (0-9) | `\d{3}` matches "123" |
| `\D` | Non-digit | `\D+` matches "abc" |
| `\w` | Word character (a-z, A-Z, 0-9, _) | `\w+` matches "hello_123" |
| `\W` | Non-word character | `\W` matches " ", "!", "@" |
| `\s` | Whitespace (space, tab, newline) | `\s+` matches "  ", "\t\n" |
| `\S` | Non-whitespace | `\S+` matches "hello" |

## Quantifiers

| Pattern | Description | Example |
|---------|-------------|---------|
| `*` | Zero or more | `ab*c` matches "ac", "abc", "abbc" |
| `+` | One or more | `ab+c` matches "abc", "abbc" (not "ac") |
| `?` | Zero or one | `ab?c` matches "ac", "abc" |
| `{n}` | Exactly n times | `a{3}` matches "aaa" |
| `{n,}` | n or more times | `a{2,}` matches "aa", "aaa" |
| `{n,m}` | Between n and m times | `a{2,4}` matches "aa", "aaa", "aaaa" |

## Anchors

| Pattern | Description | Example |
|---------|-------------|---------|
| `^` | Start of line | `^Hello` matches "Hello world" at start |
| `$` | End of line | `world$` matches "hello world" at end |
| `\b` | Word boundary | `\bword\b` matches "word" but not "words" |

## Character Classes

| Pattern | Description | Example |
|---------|-------------|---------|
| `[abc]` | Any of a, b, or c | `[aeiou]` matches vowels |
| `[^abc]` | Not a, b, or c | `[^0-9]` matches non-digits |
| `[a-z]` | Range a to z | `[a-zA-Z]` matches letters |

## Groups and Capture

| Pattern | Description | Example |
|---------|-------------|---------|
| `(abc)` | Capture group | `(\d+)` captures digits |
| `(?:abc)` | Non-capturing group | `(?:ab)+` matches "abab" |
| `\1` | Backreference to group 1 | `(\w)\1` matches "aa", "bb" |

## Common Patterns

### Email
```
\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b
```

### URL
```
https?://[^\s]+
```

### IP Address (IPv4)
```
\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b
```

### Date (YYYY-MM-DD)
```
\d{4}-\d{2}-\d{2}
```

### Phone Number (various formats)
```
\+?\d{1,3}[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}
```

### Hex Color
```
#[0-9A-Fa-f]{6}\b
```

### HTML Tag
```
<[^>]+>
```

### Quoted String
```
"[^"]*"|'[^']*'
```

## Search Examples

### Find all errors in log
```bash
python scripts/text_grep.py "ERROR|FATAL|CRITICAL" logs/
```

### Find email addresses
```bash
python scripts/text_grep.py "[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}" file.txt
```

### Find lines starting with TODO
```bash
python scripts/text_grep.py "^TODO" src/
```

### Find function definitions (Python)
```bash
python scripts/text_grep.py "^def \w+\(" src/ --include "*.py"
```

### Find IP addresses
```bash
python scripts/text_grep.py "\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b" access.log
```

## Replace Examples

### Replace all occurrences
```bash
python scripts/text_replace.py "old" "new" file.txt
```

### Replace with capture groups
```bash
# Swap first and last name
python scripts/text_replace.py "(\w+) (\w+)" "\2, \1" names.txt

# Add quotes around words
python scripts/text_replace.py "\b(\w+)\b" '"\1"' file.txt
```

### Case conversion (using functions)
```bash
# Note: Python re.sub supports callable replacement
# For complex transformations, use Python directly
```

### Remove trailing whitespace
```bash
python scripts/text_replace.py "[ \t]+$" "" file.txt
```

### Normalize line endings to LF
```bash
python scripts/text_replace.py "\r\n" "\n" file.txt
```

## Tips

1. **Escape special characters**: Use `\` to match literal `.`, `*`, `+`, `?`, `[`, `]`, `(`, `)`, `{`, `}`, `^`, `$`, `|`, `\`
   - Example: To match "file.txt", use `file\.txt`

2. **Use raw strings in Python**: When writing regex in Python, use raw strings: `r"\d+"`

3. **Test patterns**: Always test regex patterns with dry-run (`-n`) before actual replacement

4. **Be specific**: More specific patterns reduce false matches
   - Bad: `.*` (matches everything)
   - Good: `\w+@\w+\.\w+` (matches email-like patterns)

5. **Use word boundaries**: `\b` prevents partial matches
   - `\bcat\b` matches "cat" but not "category"
