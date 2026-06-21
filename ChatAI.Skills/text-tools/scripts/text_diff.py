#!/usr/bin/env python3
"""
text_diff.py — Compare two text files with unified or side-by-side diff.

Usage:
  python text_diff.py <file1> <file2> [options]

Options:
  -u, --unified N        Unified diff with N lines of context (default: 3)
  -s, --side-by-side     Side-by-side comparison
  -w, --width N          Width for side-by-side view (default: 80)
  -i, --ignore-case      Ignore case differences
  --ignore-whitespace    Ignore whitespace changes
  --encoding ENC         Force encoding
  --json                 Output as JSON
"""

import argparse
import difflib
import sys
import json

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

def read_file_lines(filepath, encoding=None, ignore_case=False, ignore_whitespace=False):
    """Read file lines with options."""
    enc = encoding or detect_encoding(filepath)
    if not enc:
        return None, f"Cannot detect encoding for {filepath}"
    
    try:
        with open(filepath, 'r', encoding=enc, errors='replace') as f:
            lines = f.readlines()
    except Exception as e:
        return None, str(e)
    
    # Apply transformations for comparison
    processed = []
    for line in lines:
        l = line.rstrip('\n\r')
        if ignore_case:
            l = l.lower()
        if ignore_whitespace:
            l = ' '.join(l.split())
        processed.append(l)
    
    return processed, None

def unified_diff(file1, file2, lines1, lines2, context=3, use_color=True):
    """Generate unified diff output."""
    diff = list(difflib.unified_diff(lines1, lines2, 
                                      fromfile=file1, 
                                      tofile=file2,
                                      lineterm='',
                                      n=context))
    
    if not diff:
        return "Files are identical"
    
    output = []
    for line in diff:
        if use_color:
            if line.startswith('+++') or line.startswith('---'):
                output.append(f"\033[1m{line}\033[0m")
            elif line.startswith('@@'):
                output.append(f"\033[36m{line}\033[0m")
            elif line.startswith('+'):
                output.append(f"\033[32m{line}\033[0m")
            elif line.startswith('-'):
                output.append(f"\033[31m{line}\033[0m")
            else:
                output.append(line)
        else:
            output.append(line)
    
    return '\n'.join(output)

def side_by_side_diff(file1, file2, lines1, lines2, width=80, use_color=True):
    """Generate side-by-side diff output."""
    col_width = (width - 3) // 2  # 3 chars for separator
    
    output = []
    
    # Header
    if use_color:
        output.append(f"\033[1m{file1:<{col_width}} | {file2:<{col_width}}\033[0m")
        output.append(f"\033[1m{'-' * col_width}-+-{'-' * col_width}\033[0m")
    else:
        output.append(f"{file1:<{col_width}} | {file2:<{col_width}}")
        output.append(f"{'-' * col_width}-+-{'-' * col_width}")
    
    # Compare lines
    max_lines = max(len(lines1), len(lines2))
    
    for i in range(max_lines):
        line1 = lines1[i] if i < len(lines1) else ""
        line2 = lines2[i] if i < len(lines2) else ""
        
        # Truncate if needed
        line1_disp = line1[:col_width]
        line2_disp = line2[:col_width]
        
        if line1 == line2:
            # Same line
            output.append(f"{line1_disp:<{col_width}}   {line2_disp}")
        elif i >= len(lines1):
            # Added in file2
            if use_color:
                output.append(f"{'':<{col_width}} \033[32m| {line2_disp:<{col_width}}\033[0m")
            else:
                output.append(f"{'':<{col_width}} > {line2_disp}")
        elif i >= len(lines2):
            # Removed from file1
            if use_color:
                output.append(f"\033[31m{line1_disp:<{col_width}}\033[0m | {'':<{col_width}}")
            else:
                output.append(f"{line1_disp:<{col_width}} < {'':<{col_width}}")
        else:
            # Changed
            if use_color:
                output.append(f"\033[31m{line1_disp:<{col_width}}\033[0m \033[33m|\033[0m \033[32m{line2_disp:<{col_width}}\033[0m")
            else:
                output.append(f"{line1_disp:<{col_width}} ! {line2_disp}")
    
    return '\n'.join(output)

def json_diff(file1, file2, lines1, lines2):
    """Generate JSON diff output."""
    diff = list(difflib.unified_diff(lines1, lines2, fromfile=file1, tofile=file2, lineterm='', n=3))
    
    changes = []
    for line in diff:
        if line.startswith('+') and not line.startswith('+++'):
            changes.append({'type': 'add', 'line': line[1:]})
        elif line.startswith('-') and not line.startswith('---'):
            changes.append({'type': 'remove', 'line': line[1:]})
    
    return json.dumps({
        'file1': file1,
        'file2': file2,
        'identical': len(diff) == 0,
        'changes': changes,
        'diff': '\n'.join(diff)
    }, ensure_ascii=False, indent=2)

def main():
    parser = argparse.ArgumentParser(description='Compare text files')
    parser.add_argument('file1', help='First file')
    parser.add_argument('file2', help='Second file')
    parser.add_argument('-u', '--unified', type=int, nargs='?', const=3, default=None, help='Unified diff')
    parser.add_argument('-s', '--side-by-side', action='store_true', help='Side-by-side view')
    parser.add_argument('-w', '--width', type=int, default=80, help='Width for side-by-side')
    parser.add_argument('-i', '--ignore-case', action='store_true', help='Ignore case')
    parser.add_argument('--ignore-whitespace', action='store_true', help='Ignore whitespace')
    parser.add_argument('--encoding', help='Force encoding')
    parser.add_argument('--json', action='store_true', help='JSON output')
    parser.add_argument('--no-color', action='store_true', help='Disable colors')
    
    args = parser.parse_args()
    
    # Read files
    lines1, err1 = read_file_lines(args.file1, args.encoding, args.ignore_case, args.ignore_whitespace)
    if err1:
        print(f"ERROR reading {args.file1}: {err1}", file=sys.stderr)
        sys.exit(1)
    
    lines2, err2 = read_file_lines(args.file2, args.encoding, args.ignore_case, args.ignore_whitespace)
    if err2:
        print(f"ERROR reading {args.file2}: {err2}", file=sys.stderr)
        sys.exit(1)
    
    # Generate diff
    use_color = not args.no_color and sys.stdout.isatty()
    
    if args.json:
        print(json_diff(args.file1, args.file2, lines1, lines2))
    elif args.side_by_side:
        print(side_by_side_diff(args.file1, args.file2, lines1, lines2, args.width, use_color))
    else:
        context = args.unified if args.unified is not None else 3
        print(unified_diff(args.file1, args.file2, lines1, lines2, context, use_color))

if __name__ == '__main__':
    main()
