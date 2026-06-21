#!/usr/bin/env python3
"""
text_grep.py — Fast text search in files (grep-like).
Supports: regex, recursive search, context lines, count, invert match, ignore case.
All files expected in UTF-8; falls back to encoding detection if needed.

Usage:
  python text_grep.py <pattern> <path> [options]

Options:
  -r, --recursive        Recursive search in directories
  -i, --ignore-case      Case-insensitive search
  -n, --line-numbers     Show line numbers
  -c, --count            Show only match count per file
  -v, --invert           Invert match (show non-matching lines)
  -l, --files-only       Show only filenames with matches
  -C, --context N        Show N lines of context before and after
  -B, --before N         Show N lines before match
  -A, --after N          Show N lines after match
  --encoding ENC         Force encoding (default: utf-8, auto-detect on failure)
  --include GLOB         Only search files matching glob pattern (e.g. "*.py")
  --exclude GLOB         Exclude files matching glob pattern
  --no-color             Disable colored output
"""

import argparse
import os
import re
import sys
import fnmatch
import json

def detect_encoding(filepath):
    """Try to detect file encoding by reading BOM or trying common encodings."""
    # Check BOM
    with open(filepath, 'rb') as f:
        raw = f.read(4)
    if raw.startswith(b'\xef\xbb\xbf'):
        return 'utf-8-sig'
    if raw.startswith(b'\xff\xfe'):
        return 'utf-16-le'
    if raw.startswith(b'\xfe\xff'):
        return 'utf-16-be'
    # Try common encodings
    for enc in ['utf-8', 'windows-1251', 'windows-1252', 'latin-1', 'cp437']:
        try:
            with open(filepath, 'r', encoding=enc) as f:
                f.read()
            return enc
        except (UnicodeDecodeError, UnicodeError):
            continue
    return None

def read_file_lines(filepath, encoding=None):
    """Read file lines with encoding handling."""
    enc = encoding
    if not enc:
        enc = detect_encoding(filepath)
    if not enc:
        return None, f"Cannot detect encoding for {filepath}"
    try:
        with open(filepath, 'r', encoding=enc, errors='replace') as f:
            return f.readlines(), None
    except Exception as e:
        return None, str(e)

def collect_files(path, recursive=True, include=None, exclude=None):
    """Collect files to search."""
    files = []
    if os.path.isfile(path):
        files.append(path)
    elif os.path.isdir(path):
        if recursive:
            for root, dirs, filenames in os.walk(path):
                # Skip hidden directories
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                for fname in sorted(filenames):
                    if fname.startswith('.'):
                        continue
                    if include and not fnmatch.fnmatch(fname, include):
                        continue
                    if exclude and fnmatch.fnmatch(fname, exclude):
                        continue
                    files.append(os.path.join(root, fname))
        else:
            for fname in sorted(os.listdir(path)):
                fpath = os.path.join(path, fname)
                if os.path.isfile(fpath):
                    if include and not fnmatch.fnmatch(fname, include):
                        continue
                    if exclude and fnmatch.fnmatch(fname, exclude):
                        continue
                    files.append(fpath)
    return files

def grep_file(filepath, pattern, ignore_case=False, invert=False, context_before=0, context_after=0, encoding=None):
    """Search pattern in file, return matches with metadata."""
    lines, err = read_file_lines(filepath, encoding)
    if err:
        return None, err
    
    flags = re.IGNORECASE if ignore_case else 0
    try:
        regex = re.compile(pattern, flags)
    except re.error as e:
        return None, f"Invalid regex: {e}"
    
    matches = []
    for i, line in enumerate(lines):
        is_match = bool(regex.search(line.rstrip('\n\r')))
        if invert:
            is_match = not is_match
        if is_match:
            start = max(0, i - context_before)
            end = min(len(lines), i + context_after + 1)
            matches.append({
                'line_num': i + 1,
                'line': line.rstrip('\n\r'),
                'context_before': [(j+1, lines[j].rstrip('\n\r')) for j in range(start, i)],
                'context_after': [(j+1, lines[j].rstrip('\n\r')) for j in range(i+1, end)],
            })
    
    return matches, None

def format_output(results, show_line_numbers=True, use_color=True, count_only=False, files_only=False):
    """Format grep results for display."""
    output = []
    
    for filepath, matches, err in results:
        if err:
            output.append(f"ERROR: {filepath}: {err}")
            continue
        
        if files_only:
            if matches:
                output.append(filepath)
            continue
        
        if count_only:
            output.append(f"{filepath}: {len(matches)}")
            continue
        
        if not matches:
            continue
        
        if len(results) > 1:
            if use_color:
                output.append(f"\033[1;35m=== {filepath} ===\033[0m")
            else:
                output.append(f"=== {filepath} ===")
        
        for idx, m in enumerate(matches):
            # Context before
            for ctx_num, ctx_line in m['context_before']:
                if use_color:
                    output.append(f"\033[36m{ctx_num}\033[0m-{ctx_line}")
                else:
                    output.append(f"{ctx_num}-{ctx_line}")
            
            # Match line
            line_prefix = f"{m['line_num']}:" if show_line_numbers else ""
            if use_color:
                output.append(f"\033[1;33m{line_prefix}\033[0m{m['line']}")
            else:
                output.append(f"{line_prefix}{m['line']}")
            
            # Context after
            for ctx_num, ctx_line in m['context_after']:
                if use_color:
                    output.append(f"\033[36m{ctx_num}\033[0m-{ctx_line}")
                else:
                    output.append(f"{ctx_num}-{ctx_line}")
            
            # Separator between non-adjacent matches
            if idx < len(matches) - 1:
                next_num = matches[idx+1]['line_num']
                if next_num - m['line_num'] > 1:
                    output.append("--")
    
    return '\n'.join(output)

def main():
    parser = argparse.ArgumentParser(description='Search text in files (grep-like)')
    parser.add_argument('pattern', help='Search pattern (regex)')
    parser.add_argument('path', help='File or directory to search')
    parser.add_argument('-r', '--recursive', action='store_true', help='Recursive search')
    parser.add_argument('-i', '--ignore-case', action='store_true', help='Case-insensitive')
    parser.add_argument('-n', '--line-numbers', action='store_true', default=True, help='Show line numbers')
    parser.add_argument('-c', '--count', action='store_true', help='Count matches only')
    parser.add_argument('-v', '--invert', action='store_true', help='Invert match')
    parser.add_argument('-l', '--files-only', action='store_true', help='Show filenames only')
    parser.add_argument('-C', '--context', type=int, default=0, help='Context lines')
    parser.add_argument('-B', '--before', type=int, default=0, help='Lines before match')
    parser.add_argument('-A', '--after', type=int, default=0, help='Lines after match')
    parser.add_argument('--encoding', help='Force encoding')
    parser.add_argument('--include', help='Include glob pattern')
    parser.add_argument('--exclude', help='Exclude glob pattern')
    parser.add_argument('--no-color', action='store_true', help='Disable colors')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    args = parser.parse_args()
    
    # Determine context
    ctx_before = args.before or args.context
    ctx_after = args.after or args.context
    
    # Collect files
    files = collect_files(args.path, recursive=args.recursive, include=args.include, exclude=args.exclude)
    
    if not files:
        print(f"No files found in: {args.path}", file=sys.stderr)
        sys.exit(1)
    
    # Search
    results = []
    total_matches = 0
    for fpath in files:
        matches, err = grep_file(fpath, args.pattern, 
                                  ignore_case=args.ignore_case, 
                                  invert=args.invert,
                                  context_before=ctx_before,
                                  context_after=ctx_after,
                                  encoding=args.encoding)
        if matches is not None:
            results.append((fpath, matches, err))
            total_matches += len(matches)
        else:
            results.append((fpath, [], err))
    
    # Output
    if args.json:
        json_results = []
        for fpath, matches, err in results:
            json_results.append({
                'file': fpath,
                'matches': [{'line_num': m['line_num'], 'line': m['line']} for m in matches],
                'count': len(matches),
                'error': err
            })
        print(json.dumps({'total_matches': total_matches, 'files': json_results}, ensure_ascii=False, indent=2))
    else:
        use_color = not args.no_color and sys.stdout.isatty()
        output = format_output(results, use_color=use_color, count_only=args.count, files_only=args.files_only)
        if output:
            print(output)
        
        if not args.count and not args.files_only:
            print(f"\n--- {total_matches} match(es) in {len(files)} file(s) ---")

if __name__ == '__main__':
    main()
