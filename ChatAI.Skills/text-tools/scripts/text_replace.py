#!/usr/bin/env python3
"""
text_replace.py — Replace text in files with regex support.
Supports: single file or batch replacement, backup creation, dry-run mode.

Usage:
  python text_replace.py <pattern> <replacement> <path> [options]

Options:
  -r, --recursive        Process directories recursively
  -i, --ignore-case      Case-insensitive replacement
  -n, --dry-run          Show what would be changed without modifying files
  -b, --backup           Create .bak backup before modification
  --encoding ENC         Force encoding (default: utf-8, auto-detect on failure)
  --include GLOB         Only process files matching glob pattern
  --exclude GLOB         Exclude files matching glob pattern
  --count                Show only count of replacements per file
"""

import argparse
import os
import re
import sys
import fnmatch
import shutil

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

def collect_files(path, recursive=True, include=None, exclude=None):
    """Collect files to process."""
    files = []
    if os.path.isfile(path):
        files.append(path)
    elif os.path.isdir(path):
        if recursive:
            for root, dirs, filenames in os.walk(path):
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

def replace_in_file(filepath, pattern, replacement, ignore_case=False, encoding=None, dry_run=False, backup=False):
    """Replace pattern in file, return count of replacements."""
    enc = encoding or detect_encoding(filepath)
    if not enc:
        return None, f"Cannot detect encoding for {filepath}"
    
    try:
        with open(filepath, 'r', encoding=enc, errors='replace') as f:
            content = f.read()
    except Exception as e:
        return None, str(e)
    
    flags = re.IGNORECASE if ignore_case else 0
    try:
        regex = re.compile(pattern, flags)
    except re.error as e:
        return None, f"Invalid regex: {e}"
    
    # Count matches
    matches = regex.findall(content)
    count = len(matches)
    
    if count == 0:
        return 0, None
    
    if not dry_run:
        # Create backup if requested
        if backup:
            backup_path = filepath + '.bak'
            shutil.copy2(filepath, backup_path)
        
        # Perform replacement
        new_content = regex.sub(replacement, content)
        
        # Write back
        try:
            with open(filepath, 'w', encoding=enc) as f:
                f.write(new_content)
        except Exception as e:
            return None, f"Failed to write: {e}"
    
    return count, None

def main():
    parser = argparse.ArgumentParser(description='Replace text in files')
    parser.add_argument('pattern', help='Search pattern (regex)')
    parser.add_argument('replacement', help='Replacement text')
    parser.add_argument('path', help='File or directory to process')
    parser.add_argument('-r', '--recursive', action='store_true', help='Recursive processing')
    parser.add_argument('-i', '--ignore-case', action='store_true', help='Case-insensitive')
    parser.add_argument('-n', '--dry-run', action='store_true', help='Show changes without modifying')
    parser.add_argument('-b', '--backup', action='store_true', help='Create .bak backups')
    parser.add_argument('--encoding', help='Force encoding')
    parser.add_argument('--include', help='Include glob pattern')
    parser.add_argument('--exclude', help='Exclude glob pattern')
    parser.add_argument('--count', action='store_true', help='Show count only')
    
    args = parser.parse_args()
    
    files = collect_files(args.path, recursive=args.recursive, include=args.include, exclude=args.exclude)
    
    if not files:
        print(f"No files found in: {args.path}", file=sys.stderr)
        sys.exit(1)
    
    total_replacements = 0
    modified_files = 0
    
    for fpath in files:
        count, err = replace_in_file(fpath, args.pattern, args.replacement,
                                      ignore_case=args.ignore_case,
                                      encoding=args.encoding,
                                      dry_run=args.dry_run,
                                      backup=args.backup)
        
        if err:
            print(f"ERROR: {fpath}: {err}", file=sys.stderr)
            continue
        
        if count > 0:
            modified_files += 1
            total_replacements += count
            
            if args.count:
                print(f"{fpath}: {count}")
            elif args.dry_run:
                print(f"Would replace {count} occurrence(s) in: {fpath}")
            else:
                print(f"Replaced {count} occurrence(s) in: {fpath}")
    
    # Summary
    action = "Would replace" if args.dry_run else "Replaced"
    print(f"\n{action} {total_replacements} occurrence(s) in {modified_files} file(s)")

if __name__ == '__main__':
    main()
