#!/usr/bin/env python3
"""
text_process.py — Text processing utilities: dedup, sort, extract columns.

Usage:
  python text_process.py <command> <file> [options]

Commands:
  dedup                  Remove duplicate lines
  sort                   Sort lines
  columns                Extract columns from CSV/TSV
  unique                 Show only unique lines (no duplicates at all)
  count                  Count lines/words/chars
  head N                 Show first N lines
  tail N                 Show last N lines

Options for dedup:
  -i, --ignore-case      Case-insensitive dedup
  -k, --keep-first       Keep first occurrence (default)
  --keep-last            Keep last occurrence
  --sorted               Input is already sorted (faster)

Options for sort:
  -r, --reverse          Reverse sort
  -n, --numeric          Numeric sort
  -i, --ignore-case      Case-insensitive sort
  -u, --unique           Sort and remove duplicates
  -k, --key N            Sort by column N (1-based)

Options for columns:
  -d, --delimiter CHAR   Column delimiter (default: auto-detect , or \t)
  -c, --columns N,M,...  Columns to extract (1-based, comma-separated)
  --header               Keep header row
  --names                Show column names only

General options:
  --encoding ENC         Force encoding
  -o, --output FILE      Output to file instead of stdout
"""

import argparse
import csv
import sys
import os

def detect_encoding(filepath):
    """Try to detect file encoding."""
    with open(filepath, 'rb') as f:
        raw = f.read(4)
    if raw.startswith(b'\xef\xbb\xbf'):
        return 'utf-8-sig'
    if raw.startswith(b'\xff\xfe'):
        return 'utf-16-le'
    if raw.startswith(b'\xfe\xff'):
        return 'utf-16-be'
    for enc in ['utf-8', 'windows-1251', 'windows-1252', 'latin-1']:
        try:
            with open(filepath, 'r', encoding=enc) as f:
                f.read()
            return enc
        except (UnicodeDecodeError, UnicodeError):
            continue
    return None

def read_file(filepath, encoding=None):
    """Read file lines."""
    enc = encoding or detect_encoding(filepath)
    if not enc:
        return None, f"Cannot detect encoding for {filepath}"
    try:
        with open(filepath, 'r', encoding=enc, errors='replace') as f:
            return f.readlines(), None
    except Exception as e:
        return None, str(e)

def write_output(lines, output_file=None, encoding='utf-8'):
    """Write output to file or stdout."""
    if output_file:
        with open(output_file, 'w', encoding=encoding) as f:
            f.write('\n'.join(lines) + '\n')
    else:
        print('\n'.join(lines))

def cmd_dedup(lines, args):
    """Remove duplicate lines."""
    seen = set()
    result = []
    
    for line in lines:
        key = line.strip()
        if args.ignore_case:
            key = key.lower()
        
        if key not in seen:
            seen.add(key)
            result.append(line.rstrip('\n\r'))
    
    return result

def cmd_sort(lines, args):
    """Sort lines."""
    # Remove newlines
    clean_lines = [l.rstrip('\n\r') for l in lines]
    
    if args.numeric:
        # Try to extract numbers for sorting
        def sort_key(line):
            parts = line.split()
            if args.key:
                try:
                    return float(parts[args.key - 1])
                except (IndexError, ValueError):
                    return float('inf')
            else:
                try:
                    return float(line.split()[0])
                except (ValueError, IndexError):
                    return float('inf')
        clean_lines.sort(key=sort_key, reverse=args.reverse)
    else:
        if args.key:
            def sort_key(line):
                parts = line.split()
                try:
                    val = parts[args.key - 1]
                    return val.lower() if args.ignore_case else val
                except IndexError:
                    return ''
            clean_lines.sort(key=sort_key, reverse=args.reverse)
        else:
            if args.ignore_case:
                clean_lines.sort(key=str.lower, reverse=args.reverse)
            else:
                clean_lines.sort(reverse=args.reverse)
    
    if args.unique:
        seen = set()
        unique_lines = []
        for line in clean_lines:
            key = line.lower() if args.ignore_case else line
            if key not in seen:
                seen.add(key)
                unique_lines.append(line)
        return unique_lines
    
    return clean_lines

def cmd_columns(lines, args):
    """Extract columns from CSV/TSV."""
    if not lines:
        return []
    
    # Auto-detect delimiter
    delimiter = args.delimiter
    if not delimiter:
        first_line = lines[0]
        if '\t' in first_line:
            delimiter = '\t'
        elif ',' in first_line:
            delimiter = ','
        else:
            delimiter = ','
    
    # Parse with csv module for proper handling
    reader = csv.reader(lines, delimiter=delimiter)
    rows = list(reader)
    
    if not rows:
        return []
    
    # Show column names only
    if args.names:
        if rows:
            return [f"Column {i+1}: {name}" for i, name in enumerate(rows[0])]
        return []
    
    # Determine which columns to extract
    if args.columns:
        col_indices = [int(c) - 1 for c in args.columns.split(',')]
    else:
        col_indices = list(range(len(rows[0])))
    
    # Extract columns
    result = []
    start_idx = 1 if args.header else 0
    
    if args.header and rows:
        # Keep header
        header = [rows[0][i] if i < len(rows[0]) else '' for i in col_indices]
        result.append(delimiter.join(header))
    
    for row in rows[start_idx:]:
        extracted = [row[i] if i < len(row) else '' for i in col_indices]
        result.append(delimiter.join(extracted))
    
    return result

def cmd_unique(lines, args):
    """Show only lines that appear exactly once."""
    from collections import Counter
    
    clean_lines = [l.rstrip('\n\r') for l in lines]
    
    if args.ignore_case:
        counter = Counter(l.lower() for l in clean_lines)
        return [l for l in clean_lines if counter[l.lower()] == 1]
    else:
        counter = Counter(clean_lines)
        return [l for l in clean_lines if counter[l] == 1]

def cmd_count(lines, args):
    """Count lines, words, characters."""
    clean_lines = [l.rstrip('\n\r') for l in lines]
    line_count = len(clean_lines)
    word_count = sum(len(l.split()) for l in clean_lines)
    char_count = sum(len(l) for l in clean_lines)
    
    return [f"Lines: {line_count}", f"Words: {word_count}", f"Characters: {char_count}"]

def cmd_head(lines, args):
    """Show first N lines."""
    n = int(args.n) if hasattr(args, 'n') and args.n else 10
    return [l.rstrip('\n\r') for l in lines[:n]]

def cmd_tail(lines, args):
    """Show last N lines."""
    n = int(args.n) if hasattr(args, 'n') and args.n else 10
    return [l.rstrip('\n\r') for l in lines[-n:]]

def main():
    parser = argparse.ArgumentParser(description='Text processing utilities')
    parser.add_argument('command', choices=['dedup', 'sort', 'columns', 'unique', 'count', 'head', 'tail'],
                       help='Command to execute')
    parser.add_argument('file', help='Input file')
    parser.add_argument('-i', '--ignore-case', action='store_true', help='Case-insensitive')
    parser.add_argument('-r', '--reverse', action='store_true', help='Reverse order')
    parser.add_argument('-n', '--numeric', action='store_true', help='Numeric sort')
    parser.add_argument('-u', '--unique', action='store_true', help='Unique only')
    parser.add_argument('-k', '--key', type=int, help='Sort/extract by column N')
    parser.add_argument('-d', '--delimiter', help='Column delimiter')
    parser.add_argument('-c', '--columns', help='Columns to extract (1-based, comma-separated)')
    parser.add_argument('--header', action='store_true', help='Keep header row')
    parser.add_argument('--names', action='store_true', help='Show column names only')
    parser.add_argument('--sorted', action='store_true', help='Input is sorted (for dedup)')
    parser.add_argument('--keep-last', action='store_true', help='Keep last occurrence (for dedup)')
    parser.add_argument('--encoding', help='Force encoding')
    parser.add_argument('-o', '--output', help='Output file')
    
    args = parser.parse_args()
    
    # Read file
    lines, err = read_file(args.file, args.encoding)
    if err:
        print(f"ERROR: {err}", file=sys.stderr)
        sys.exit(1)
    
    # Execute command
    if args.command == 'dedup':
        result = cmd_dedup(lines, args)
    elif args.command == 'sort':
        result = cmd_sort(lines, args)
    elif args.command == 'columns':
        result = cmd_columns(lines, args)
    elif args.command == 'unique':
        result = cmd_unique(lines, args)
    elif args.command == 'count':
        result = cmd_count(lines, args)
    elif args.command == 'head':
        result = cmd_head(lines, args)
    elif args.command == 'tail':
        result = cmd_tail(lines, args)
    else:
        print(f"Unknown command: {args.command}", file=sys.stderr)
        sys.exit(1)
    
    # Output
    write_output(result, args.output)

if __name__ == '__main__':
    main()
