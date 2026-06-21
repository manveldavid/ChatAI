---
name: text-tools
description: Comprehensive toolkit for working with text files. Use this skill whenever the user needs to search text in files (grep, find text, search patterns), replace text in files (find and replace, batch replace), compare files (diff, compare text files), process text (remove duplicates, sort lines, extract CSV columns, count lines/words), check text file formatting (encoding, line endings, trailing whitespace, tabs), or validate structured files (CSV, JSON, YAML). Always trigger when the user mentions text search, grep, find in files, replace text, compare files, diff, sort lines, remove duplicates, CSV columns, check encoding, validate JSON/YAML/CSV, or any text file manipulation task. This skill works with any text files in UTF-8 or other encodings with automatic detection.
---

# Text Tools

A comprehensive toolkit for efficient text file operations. All tools support UTF-8 by default with automatic encoding detection for other encodings.

## Quick Reference

### Search (grep)
```bash
python scripts/text_grep.py <pattern> <path> [options]
```
Search for text patterns in files with regex support.

**Common use cases:**
- `python scripts/text_grep.py "error" logs/` — search for "error" in logs directory
- `python scripts/text_grep.py -r "TODO" src/` — recursive search for TODO
- `python scripts/text_grep.py -i "warning" app.log` — case-insensitive search
- `python scripts/text_grep.py "def.*test" tests/ --include "*.py"` — search in Python files only
- `python scripts/text_grep.py -C 3 "exception" logs/` — show 3 lines of context
- `python scripts/text_grep.py -c "error" logs/` — count matches per file
- `python scripts/text_grep.py -l "error" logs/` — show only filenames
- `python scripts/text_grep.py --json "error" logs/` — JSON output for programmatic use

**Key options:**
- `-r, --recursive` — search directories recursively
- `-i, --ignore-case` — case-insensitive search
- `-n, --line-numbers` — show line numbers (default: on)
- `-c, --count` — show match count only
- `-v, --invert` — show non-matching lines
- `-l, --files-only` — show filenames only
- `-C N, --context N` — show N lines before and after match
- `-B N, --before N` — show N lines before match
- `-A N, --after N` — show N lines after match
- `--include GLOB` — only search files matching pattern (e.g., "*.py")
- `--exclude GLOB` — exclude files matching pattern
- `--json` — output as JSON

### Replace Text
```bash
python scripts/text_replace.py <pattern> <replacement> <path> [options]
```
Replace text in files with regex support.

**Common use cases:**
- `python scripts/text_replace.py "old" "new" file.txt` — replace in single file
- `python scripts/text_replace.py -r "foo" "bar" src/` — recursive replacement
- `python scripts/text_replace.py -n "old" "new" file.txt` — dry run (show what would change)
- `python scripts/text_replace.py -b "old" "new" file.txt` — create backup before replacing
- `python scripts/text_replace.py -i "error" "warning" logs/` — case-insensitive replacement

**Key options:**
- `-r, --recursive` — process directories recursively
- `-i, --ignore-case` — case-insensitive replacement
- `-n, --dry-run` — show changes without modifying files
- `-b, --backup` — create .bak backup files
- `--include GLOB` — only process matching files
- `--exclude GLOB` — exclude matching files
- `--count` — show count only

**Regex replacement:** Use `\1`, `\2` for capture groups:
```bash
python scripts/text_replace.py "(\w+)@(\w+)" "\1 at \2" emails.txt
```

### Compare Files (diff)
```bash
python scripts/text_diff.py <file1> <file2> [options]
```
Compare two text files.

**Common use cases:**
- `python scripts/text_diff.py old.txt new.txt` — unified diff (default)
- `python scripts/text_diff.py -s old.txt new.txt` — side-by-side comparison
- `python scripts/text_diff.py -u 5 old.txt new.txt` — unified diff with 5 lines context
- `python scripts/text_diff.py -i old.txt new.txt` — ignore case differences
- `python scripts/text_diff.py --json old.txt new.txt` — JSON output

**Key options:**
- `-u N, --unified N` — unified diff with N lines context (default: 3)
- `-s, --side-by-side` — side-by-side view
- `-w N, --width N` — width for side-by-side view (default: 80)
- `-i, --ignore-case` — ignore case
- `--ignore-whitespace` — ignore whitespace changes
- `--json` — JSON output

### Process Text
```bash
python scripts/text_process.py <command> <file> [options]
```
Text processing utilities: dedup, sort, extract columns, count, head, tail.

**Commands:**

#### Remove Duplicates
```bash
python scripts/text_process.py dedup file.txt
python scripts/text_process.py dedup -i file.txt  # case-insensitive
```
Options:
- `-i, --ignore-case` — case-insensitive dedup
- `--sorted` — input is already sorted (faster)

#### Sort Lines
```bash
python scripts/text_process.py sort file.txt
python scripts/text_process.py sort -n file.txt  # numeric sort
python scripts/text_process.py sort -r file.txt  # reverse
python scripts/text_process.py sort -u file.txt  # unique only
python scripts/text_process.py sort -k 2 file.txt  # sort by column 2
```
Options:
- `-r, --reverse` — reverse sort
- `-n, --numeric` — numeric sort
- `-i, --ignore-case` — case-insensitive
- `-u, --unique` — remove duplicates
- `-k N, --key N` — sort by column N (1-based)

#### Extract CSV Columns
```bash
python scripts/text_process.py columns data.csv -c 1,3  # extract columns 1 and 3
python scripts/text_process.py columns data.csv --names  # show column names
python scripts/text_process.py columns data.csv -d ";" -c 2  # semicolon delimiter
```
Options:
- `-d CHAR, --delimiter CHAR` — column delimiter (auto-detect by default)
- `-c N,M, --columns N,M` — columns to extract (1-based)
- `--header` — keep header row
- `--names` — show column names only

#### Other Commands
```bash
python scripts/text_process.py unique file.txt  # show only unique lines (no duplicates)
python scripts/text_process.py count file.txt   # count lines/words/chars
python scripts/text_process.py head file.txt    # first 10 lines
python scripts/text_process.py tail file.txt    # last 10 lines
```

**General options:**
- `--encoding ENC` — force encoding
- `-o FILE, --output FILE` — output to file

### Check Formatting
```bash
python scripts/text_check.py <file> [options]
```
Check text file formatting and encoding.

**Common use cases:**
- `python scripts/text_check.py file.txt` — basic checks (encoding, EOL, trailing whitespace, final newline)
- `python scripts/text_check.py --all file.txt` — all checks including BOM, tabs, multiple empty lines
- `python scripts/text_check.py --check-tabs file.txt` — check for tabs
- `python scripts/text_check.py --json file.txt` — JSON output

**Checks:**
- `--encoding` — verify encoding (default: utf-8)
- `--check-bom` — check for BOM presence
- `--check-eol` — check line endings (CRLF/LF consistency)
- `--check-trailing` — check trailing whitespace
- `--check-tabs` — check for tabs
- `--check-empty-lines` — check multiple consecutive empty lines
- `--check-final-newline` — check if file ends with newline
- `--all` — run all checks

**Key options:**
- `--encoding ENC` — expected encoding (default: utf-8)
- `--json` — JSON output

### Validate Structured Files
```bash
python scripts/text_validate.py <file> [options]
```
Validate CSV, JSON, and YAML files for correctness.

**Common use cases:**
- `python scripts/text_validate.py data.csv` — validate CSV structure
- `python scripts/text_validate.py data.csv --csv-strict` — strict validation (fail on inconsistent columns)
- `python scripts/text_validate.py config.json` — validate JSON syntax
- `python scripts/text_validate.py config.json --json-sort-keys` — check if keys are sorted
- `python scripts/text_validate.py config.yaml` — validate YAML syntax
- `python scripts/text_validate.py config.yaml --yaml-strict` — strict validation (check duplicate keys)

**CSV validation:**
- Auto-detects delimiter (comma, tab, semicolon)
- Checks column consistency
- Properly handles escaped values (quotes, newlines, commas within fields)
- Detects headers
- Options:
  - `--csv-delimiter CHAR` — force delimiter
  - `--csv-strict` — fail on any inconsistency

**JSON validation:**
- Syntax checking with line/column numbers
- Structure analysis (type, key count, array length)
- Options:
  - `--json-indent N` — check indentation (N spaces)
  - `--json-sort-keys` — verify keys are sorted alphabetically

**YAML validation:**
- Syntax checking with error location
- Structure analysis
- Options:
  - `--yaml-strict` — check for duplicate keys

**General options:**
- `--format FMT` — force format (csv, json, yaml)
- `--encoding ENC` — force encoding
- `--json` — JSON output
- `--no-color` — disable colors

## Encoding Handling


All tools automatically detect file encoding. The detection order:
1. BOM (Byte Order Mark) — UTF-8 BOM, UTF-16 LE/BE
2. Try common encodings: UTF-8, Windows-1251, Windows-1252, Latin-1

If automatic detection fails, use `--encoding` option to specify encoding explicitly:
```bash
python scripts/text_grep.py "pattern" file.txt --encoding windows-1251
```

### Encoding Detection and Conversion
```bash
python scripts/text_encoding.py <command> <file> [options]
```
Detect and convert file encodings.

**Detect encoding:**
```bash
python scripts/text_encoding.py detect file.txt
python scripts/text_encoding.py detect logs/ -r  # recursive
```

**Convert encoding:**
```bash
python scripts/text_encoding.py convert file.txt --from windows-1251 --to utf-8
python scripts/text_encoding.py convert file.txt --to utf-8 --add-bom  # add BOM
python scripts/text_encoding.py convert file.txt --to utf-8 -o output.txt  # save to new file
python scripts/text_encoding.py convert logs/ -r --to utf-8  # convert all files recursively
```

**Key options:**
- `--from ENC` — source encoding (default: auto-detect)
- `--to ENC` — target encoding (default: utf-8)
- `-o FILE` — output file (default: overwrite input)
- `--add-bom` — add BOM to output
- `--remove-bom` — remove BOM from output
- `-r, --recursive` — process directories recursively
- `--include GLOB` — only process matching files
- `--exclude GLOB` — exclude matching files


## Workflow Examples

### Find and fix issues in code
```bash
# Find all TODO comments
python scripts/text_grep.py -r "TODO" src/ --include "*.py"

# Replace deprecated function
python scripts/text_replace.py -r -n "old_func" "new_func" src/  # dry run
python scripts/text_replace.py -r -b "old_func" "new_func" src/  # with backup

# Check formatting
python scripts/text_check.py --all src/main.py
```

### Process log files
```bash
# Find errors with context
python scripts/text_grep.py -C 5 "ERROR" logs/

# Count errors per file
python scripts/text_grep.py -c "ERROR" logs/

# Extract unique error messages
python scripts/text_grep.py "ERROR: (.*)" logs/ | python scripts/text_process.py dedup -
```

### Clean up CSV data
```bash
# Show column names
python scripts/text_process.py columns data.csv --names

# Extract specific columns
python scripts/text_process.py columns data.csv -c 1,3,5 -o extracted.csv

# Remove duplicate rows
python scripts/text_process.py dedup data.csv -o clean.csv

# Sort by column
python scripts/text_process.py sort data.csv -k 2 -o sorted.csv
```

### Compare file versions
```bash
# Quick comparison
python scripts/text_diff.py old.txt new.txt

# Side-by-side for detailed review
python scripts/text_diff.py -s old.txt new.txt

# Ignore whitespace changes
python scripts/text_diff.py --ignore-whitespace old.txt new.txt
```

## Tips

1. **Always use dry-run first** for replacements: `text_replace.py -n` shows what would change without modifying files
2. **Create backups** for important files: `text_replace.py -b` creates .bak files
3. **Use glob patterns** to target specific files: `--include "*.py"` or `--exclude "*.log"`
4. **JSON output** is great for programmatic processing: add `--json` to any command
5. **Context lines** help understand grep matches: `-C 3` shows 3 lines before and after
6. **Check before commit**: run `text_check.py --all` to ensure file formatting is correct

## Troubleshooting

**Encoding issues:** If you see garbled text, specify encoding explicitly with `--encoding`

**No matches found:** Check if pattern needs escaping, or try `-i` for case-insensitive search

**Permission denied:** Check file permissions, or ensure file is not open in another program

**Large files:** All tools stream data efficiently, but for very large files (>1GB), consider using system grep for initial filtering
