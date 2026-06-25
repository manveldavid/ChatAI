#!/usr/bin/env python3
"""
text_slice.py — Line-range operations for text files.

Read, insert, delete, or replace specific line ranges. Designed for working
with large files where you need precise line-level access (e.g., read a method
body after finding it via grep).

Usage:
  python text_slice.py read   <file> [options]   Read a range of lines
  python text_slice.py insert <file> [options]   Insert lines at a position
  python text_slice.py delete <file> [options]   Delete a range of lines
  python text_slice.py replace <file> [options]  Replace a range of lines

== READ ==
  python text_slice.py read file.txt --from 100 --to 200
  python text_slice.py read file.txt --line 150 --around 50
  python text_slice.py read file.txt --last 50
  python text_slice.py read file.txt --from 100 --to 200 -n

  Options:
    --from N          Start line (1-based, inclusive, default: 1)
    --to N            End line (1-based, inclusive, default: last line)
    --line N          Center line for --around mode
    --around N        Read N lines before and after --line
    --last N          Show last N lines of file
    -n, --line-numbers  Show line numbers in output
    --no-color        Disable colored line numbers

== INSERT ==
  python text_slice.py insert file.txt --line 100 --content "new text"
  python text_slice.py insert file.txt --line 100 --file patch.txt
  python text_slice.py insert file.txt --line 100 --content "line1\\nline2"

  Options:
    --line N          Insert BEFORE this line (1-based)
    --content TEXT    Text to insert (use \\n for newlines)
    --file FILE       File whose contents to insert
    -b, --backup      Create .bak backup before modifying

== DELETE ==
  python text_slice.py delete file.txt --from 100 --to 200
  python text_slice.py delete file.txt --line 150
  python text_slice.py delete file.txt --from 100 --to 200 -n
  python text_slice.py delete file.txt --from 100 --to 200 -b

  Options:
    --from N          Start line (1-based, inclusive)
    --to N            End line (1-based, inclusive, default: same as --from)
    --line N          Delete single line
    -n, --dry-run     Show what would be deleted without modifying
    -b, --backup      Create .bak backup before modifying

== REPLACE ==
  python text_slice.py replace file.txt --from 100 --to 200 --content "new text"
  python text_slice.py replace file.txt --from 100 --to 200 --file patch.txt
  python text_slice.py replace file.txt --line 150 --content "replacement"

  Options:
    --from N          Start line (1-based, inclusive)
    --to N            End line (1-based, inclusive, default: same as --from)
    --line N          Replace single line
    --content TEXT    Replacement text (use \\n for newlines)
    --file FILE       File whose contents to use as replacement
    -n, --dry-run     Show what would change without modifying
    -b, --backup      Create .bak backup before modifying

== GENERAL OPTIONS ==
    --encoding ENC    Force encoding (default: auto-detect)
    -o, --output FILE Write output to file (for read: stdout by default;
                      for write ops: default is in-place)
    --no-color        Disable colored output
"""

import argparse
import os
import shutil
import sys


def detect_encoding(filepath):
    """Try to detect file encoding by reading BOM or trying common encodings."""
    with open(filepath, 'rb') as f:
        raw = f.read(4)
    if raw.startswith(b'\xef\xbb\xbf'):
        return 'utf-8-sig'
    if raw.startswith(b'\xff\xfe'):
        return 'utf-16-le'
    if raw.startswith(b'\xfe\xff'):
        return 'utf-16-be'
    for enc in ['utf-8', 'windows-1251', 'windows-1252', 'latin-1', 'cp437']:
        try:
            with open(filepath, 'r', encoding=enc) as f:
                f.read()
            return enc
        except (UnicodeDecodeError, UnicodeError):
            continue
    return None


def read_file_lines(filepath, encoding=None):
    """Read file lines with encoding handling. Returns (lines, error)."""
    enc = encoding or detect_encoding(filepath)
    if not enc:
        return None, f"Cannot detect encoding for {filepath}"
    try:
        with open(filepath, 'r', encoding=enc, errors='replace', newline='') as f:
            return f.readlines(), None
    except Exception as e:
        return None, str(e)


def write_file_lines(filepath, lines, encoding='utf-8'):
    """Write lines to file."""
    try:
        with open(filepath, 'w', encoding=encoding, newline='') as f:
            f.writelines(lines)
        return None
    except Exception as e:
        return str(e)


def create_backup(filepath):
    """Create a .bak backup of the file."""
    backup_path = filepath + '.bak'
    try:
        shutil.copy2(filepath, backup_path)
        return backup_path, None
    except Exception as e:
        return None, str(e)


def resolve_range(args, total_lines):
    """Resolve --from/--to/--line/--around/--last into (start, end) 0-based inclusive."""
    if hasattr(args, 'last') and args.last is not None:
        start = max(0, total_lines - args.last)
        return start, total_lines - 1

    if hasattr(args, 'around') and args.around is not None:
        center = (args.line or 1) - 1
        start = max(0, center - args.around)
        end = min(total_lines - 1, center + args.around)
        return start, end

    if getattr(args, 'line', None) is not None and getattr(args, 'from_', None) is None and getattr(args, 'around', None) is None:
        idx = args.line - 1
        return idx, idx

    start = (getattr(args, 'from_', None) or 1) - 1
    if hasattr(args, 'to') and args.to is not None:
        end = args.to - 1
    elif hasattr(args, 'line') and args.line is not None:
        end = args.line - 1
    else:
        end = total_lines - 1

    start = max(0, min(start, total_lines - 1))
    end = max(0, min(end, total_lines - 1))
    return start, end


def color_line_number(lineno, width, no_color=False):
    """Format a line number with optional ANSI color."""
    if no_color:
        return f"{lineno:>{width}}  "
    return f"\033[38;5;241m{lineno:>{width}}\033[0m  "


def cmd_read(args):
    """Read and display a range of lines."""
    lines, err = read_file_lines(args.file, args.encoding)
    if err:
        print(f"Error: {err}", file=sys.stderr)
        return 1

    total = len(lines)
    if total == 0:
        print("(empty file)", file=sys.stderr)
        return 0

    start, end = resolve_range(args, total)

    output_lines = []
    width = len(str(end + 1))
    no_color = getattr(args, 'no_color', False)
    show_numbers = getattr(args, 'line_numbers', False)

    for i in range(start, end + 1):
        line = lines[i]
        if show_numbers:
            prefix = color_line_number(i + 1, width, no_color)
            output_lines.append(prefix + line)
        else:
            output_lines.append(line)

    text = ''.join(output_lines)

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"Lines {start + 1}-{end + 1} written to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(text)
        if not text.endswith('\n'):
            sys.stdout.write('\n')

    return 0


def get_insert_content(args):
    """Get content to insert/replace from --content or --file."""
    if args.content is not None:
        return args.content.replace('\\n', '\n')
    if args.file_content:
        try:
            with open(args.file_content, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Error reading {args.file_content}: {e}", file=sys.stderr)
            return None
    print("Error: specify --content or --file", file=sys.stderr)
    return None


def cmd_insert(args):
    """Insert content before a given line."""
    lines, err = read_file_lines(args.file, args.encoding)
    if err:
        print(f"Error: {err}", file=sys.stderr)
        return 1

    content = get_insert_content(args)
    if content is None:
        return 1

    insert_at = (args.line or 1) - 1
    insert_at = max(0, min(insert_at, len(lines)))

    # Ensure content ends with newline
    if content and not content.endswith('\n'):
        content += '\n'

    # Split content into lines preserving line endings
    new_lines = []
    for part in content.split('\n'):
        if part or part == '':
            new_lines.append(part + '\n')
    # Remove trailing empty element if content ended with \n
    if new_lines and new_lines[-1] == '\n':
        new_lines.pop()

    if args.dry_run:
        print(f"Would insert {len(new_lines)} line(s) before line {insert_at + 1}:", file=sys.stderr)
        for l in new_lines[:10]:
            print(f"  + {l.rstrip()}", file=sys.stderr)
        if len(new_lines) > 10:
            print(f"  ... and {len(new_lines) - 10} more line(s)", file=sys.stderr)
        return 0

    if args.backup:
        backup, berr = create_backup(args.file)
        if berr:
            print(f"Warning: could not create backup: {berr}", file=sys.stderr)
        else:
            print(f"Backup: {backup}", file=sys.stderr)

    result = lines[:insert_at] + new_lines + lines[insert_at:]
    enc = args.encoding or detect_encoding(args.file) or 'utf-8'
    werr = write_file_lines(args.output or args.file, result, enc)
    if werr:
        print(f"Error: {werr}", file=sys.stderr)
        return 1

    target = args.output or args.file
    print(f"Inserted {len(new_lines)} line(s) before line {insert_at + 1} in {target}", file=sys.stderr)
    return 0


def cmd_delete(args):
    """Delete a range of lines."""
    lines, err = read_file_lines(args.file, args.encoding)
    if err:
        print(f"Error: {err}", file=sys.stderr)
        return 1

    total = len(lines)
    start, end = resolve_range(args, total)

    if args.dry_run:
        print(f"Would delete lines {start + 1}-{end + 1} ({end - start + 1} line(s)):", file=sys.stderr)
        for i in range(start, min(start + 10, end + 1)):
            print(f"  - {lines[i].rstrip()}", file=sys.stderr)
        if end - start + 1 > 10:
            print(f"  ... and {end - start + 1 - 10} more line(s)", file=sys.stderr)
        return 0

    if args.backup:
        backup, berr = create_backup(args.file)
        if berr:
            print(f"Warning: could not create backup: {berr}", file=sys.stderr)
        else:
            print(f"Backup: {backup}", file=sys.stderr)

    result = lines[:start] + lines[end + 1:]
    enc = args.encoding or detect_encoding(args.file) or 'utf-8'
    target = args.output or args.file
    werr = write_file_lines(target, result, enc)
    if werr:
        print(f"Error: {werr}", file=sys.stderr)
        return 1

    print(f"Deleted lines {start + 1}-{end + 1} ({end - start + 1} line(s)) from {target}", file=sys.stderr)
    return 0


def cmd_replace(args):
    """Replace a range of lines with new content."""
    lines, err = read_file_lines(args.file, args.encoding)
    if err:
        print(f"Error: {err}", file=sys.stderr)
        return 1

    total = len(lines)
    start, end = resolve_range(args, total)

    content = get_insert_content(args)
    if content is None:
        return 1

    # Ensure content ends with newline
    if content and not content.endswith('\n'):
        content += '\n'

    new_lines = []
    for part in content.split('\n'):
        if part or part == '':
            new_lines.append(part + '\n')
    if new_lines and new_lines[-1] == '\n':
        new_lines.pop()

    if args.dry_run:
        print(f"Would replace lines {start + 1}-{end + 1} ({end - start + 1} line(s)) "
              f"with {len(new_lines)} line(s):", file=sys.stderr)
        print("  Old:", file=sys.stderr)
        for i in range(start, min(start + 5, end + 1)):
            print(f"    - {lines[i].rstrip()}", file=sys.stderr)
        if end - start + 1 > 5:
            print(f"    ... ({end - start + 1 - 5} more old line(s))", file=sys.stderr)
        print("  New:", file=sys.stderr)
        for l in new_lines[:5]:
            print(f"    + {l.rstrip()}", file=sys.stderr)
        if len(new_lines) > 5:
            print(f"    ... ({len(new_lines) - 5} more new line(s))", file=sys.stderr)
        return 0

    if args.backup:
        backup, berr = create_backup(args.file)
        if berr:
            print(f"Warning: could not create backup: {berr}", file=sys.stderr)
        else:
            print(f"Backup: {backup}", file=sys.stderr)

    result = lines[:start] + new_lines + lines[end + 1:]
    enc = args.encoding or detect_encoding(args.file) or 'utf-8'
    target = args.output or args.file
    werr = write_file_lines(target, result, enc)
    if werr:
        print(f"Error: {werr}", file=sys.stderr)
        return 1

    print(f"Replaced lines {start + 1}-{end + 1} with {len(new_lines)} line(s) in {target}",
          file=sys.stderr)
    return 0


def main():
    parser = argparse.ArgumentParser(
        description='Line-range operations for text files.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    subparsers = parser.add_subparsers(dest='command', help='Operation to perform')

    # === READ ===
    p_read = subparsers.add_parser('read', help='Read a range of lines')
    p_read.add_argument('file', help='Input file')
    p_read.add_argument('--from', dest='from_', type=int, help='Start line (1-based, inclusive)')
    p_read.add_argument('--to', type=int, help='End line (1-based, inclusive)')
    p_read.add_argument('--line', type=int, help='Center line for --around mode')
    p_read.add_argument('--around', type=int, help='Lines before and after --line')
    p_read.add_argument('--last', type=int, help='Show last N lines')
    p_read.add_argument('-n', '--line-numbers', action='store_true', help='Show line numbers')
    p_read.add_argument('--no-color', action='store_true', help='Disable colored line numbers')
    p_read.add_argument('--encoding', help='Force encoding')
    p_read.add_argument('-o', '--output', help='Output to file')

    # === INSERT ===
    p_insert = subparsers.add_parser('insert', help='Insert lines at a position')
    p_insert.add_argument('file', help='Target file')
    p_insert.add_argument('--line', type=int, required=True, help='Insert BEFORE this line (1-based)')
    p_insert.add_argument('--content', help='Text to insert (use \\n for newlines)')
    p_insert.add_argument('--file', dest='file_content', help='File whose contents to insert')
    p_insert.add_argument('-b', '--backup', action='store_true', help='Create .bak backup')
    p_insert.add_argument('-n', '--dry-run', action='store_true', help='Show what would be inserted')
    p_insert.add_argument('--encoding', help='Force encoding')
    p_insert.add_argument('-o', '--output', help='Output to file instead of in-place')

    # === DELETE ===
    p_delete = subparsers.add_parser('delete', help='Delete a range of lines')
    p_delete.add_argument('file', help='Target file')
    p_delete.add_argument('--from', dest='from_', type=int, help='Start line (1-based, inclusive)')
    p_delete.add_argument('--to', type=int, help='End line (1-based, inclusive)')
    p_delete.add_argument('--line', type=int, help='Delete single line')
    p_delete.add_argument('-n', '--dry-run', action='store_true', help='Show what would be deleted')
    p_delete.add_argument('-b', '--backup', action='store_true', help='Create .bak backup')
    p_delete.add_argument('--encoding', help='Force encoding')
    p_delete.add_argument('-o', '--output', help='Output to file instead of in-place')

    # === REPLACE ===
    p_replace = subparsers.add_parser('replace', help='Replace a range of lines')
    p_replace.add_argument('file', help='Target file')
    p_replace.add_argument('--from', dest='from_', type=int, help='Start line (1-based, inclusive)')
    p_replace.add_argument('--to', type=int, help='End line (1-based, inclusive)')
    p_replace.add_argument('--line', type=int, help='Replace single line')
    p_replace.add_argument('--content', help='Replacement text (use \\n for newlines)')
    p_replace.add_argument('--file', dest='file_content', help='File with replacement content')
    p_replace.add_argument('-n', '--dry-run', action='store_true', help='Show what would change')
    p_replace.add_argument('-b', '--backup', action='store_true', help='Create .bak backup')
    p_replace.add_argument('--encoding', help='Force encoding')
    p_replace.add_argument('-o', '--output', help='Output to file instead of in-place')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    commands = {
        'read': cmd_read,
        'insert': cmd_insert,
        'delete': cmd_delete,
        'replace': cmd_replace,
    }
    return commands[args.command](args)


if __name__ == '__main__':
    sys.exit(main() or 0)
