#!/usr/bin/env python3
"""
text_validate.py — Validate structured text files (CSV, JSON, YAML).

Usage:
  python text_validate.py <file> [options]

Options:
  --format FMT           Force format (csv, json, yaml, auto-detect by extension)
  --csv-delimiter CHAR   CSV delimiter (default: auto-detect)
  --csv-strict           Strict CSV validation (check consistent columns)
  --json-indent N        Check JSON indentation (N spaces)
  --json-sort-keys       Check if JSON keys are sorted
  --yaml-strict          Strict YAML validation
  --fix                  Attempt to fix issues (where possible)
  --json                 Output as JSON
"""

import argparse
import csv
import json
import sys
import os
from collections import Counter

def detect_format(filepath):
    """Detect file format by extension."""
    ext = os.path.splitext(filepath)[1].lower()
    format_map = {
        '.csv': 'csv',
        '.tsv': 'csv',
        '.json': 'json',
        '.jsonl': 'json',
        '.yaml': 'yaml',
        '.yml': 'yaml',
    }
    return format_map.get(ext)

def detect_encoding(filepath):
    """Detect file encoding."""
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

def validate_csv(filepath, delimiter=None, strict=False, encoding=None):
    """Validate CSV file."""
    enc = encoding or detect_encoding(filepath)
    if not enc:
        return {'valid': False, 'errors': ['Cannot detect encoding'], 'warnings': []}
    
    try:
        with open(filepath, 'r', encoding=enc, errors='replace') as f:
            content = f.read()
    except Exception as e:
        return {'valid': False, 'errors': [str(e)], 'warnings': []}
    
    errors = []
    warnings = []
    info = {}
    
    # Auto-detect delimiter
    if not delimiter:
        first_line = content.split('\n')[0]
        if '\t' in first_line:
            delimiter = '\t'
        elif ';' in first_line and first_line.count(';') > first_line.count(','):
            delimiter = ';'
        else:
            delimiter = ','
    
    # Parse CSV
    try:
        reader = csv.reader(content.splitlines(), delimiter=delimiter)
        rows = list(reader)
    except csv.Error as e:
        return {'valid': False, 'errors': [f'CSV parse error: {e}'], 'warnings': []}
    
    if not rows:
        warnings.append('Empty file')
        return {'valid': True, 'errors': [], 'warnings': warnings, 'info': {'rows': 0}}
    
    # Check consistency
    col_counts = [len(row) for row in rows]
    unique_counts = set(col_counts)
    
    info['rows'] = len(rows)
    info['columns'] = col_counts[0] if col_counts else 0
    info['delimiter'] = repr(delimiter)
    
    if len(unique_counts) > 1:
        if strict:
            errors.append(f'Inconsistent column count: found {unique_counts}')
        else:
            warnings.append(f'Inconsistent column count: found {unique_counts}')
        
        # Find rows with different column counts
        expected = col_counts[0]
        for i, count in enumerate(col_counts, 1):
            if count != expected:
                errors.append(f'Row {i}: expected {expected} columns, got {count}')
                if len(errors) > 10:
                    errors.append('... (more errors)')
                    break
    
    # Check for empty rows
    empty_rows = [i for i, row in enumerate(rows, 1) if not any(cell.strip() for cell in row)]
    if empty_rows:
        warnings.append(f'Found {len(empty_rows)} empty rows')
    
    # Check for trailing commas (empty last column)
    trailing_empty = []
    for i, row in enumerate(rows, 1):
        if row and not row[-1].strip():
            trailing_empty.append(i)
    if trailing_empty:
        warnings.append(f'Found {len(trailing_empty)} rows with trailing empty cells')
    
    # Check header (if present)
    if rows and all(isinstance(cell, str) and not cell.replace('.', '').replace('-', '').isdigit() 
                    for cell in rows[0]):
        info['has_header'] = True
        info['header'] = rows[0]
    else:
        info['has_header'] = False
    
    valid = len(errors) == 0
    return {'valid': valid, 'errors': errors, 'warnings': warnings, 'info': info}

def validate_json(filepath, check_indent=None, check_sorted=False, encoding=None):
    """Validate JSON file."""
    enc = encoding or detect_encoding(filepath)
    if not enc:
        return {'valid': False, 'errors': ['Cannot detect encoding'], 'warnings': []}
    
    try:
        with open(filepath, 'r', encoding=enc, errors='replace') as f:
            content = f.read()
    except Exception as e:
        return {'valid': False, 'errors': [str(e)], 'warnings': []}
    
    errors = []
    warnings = []
    info = {}
    
    # Parse JSON
    try:
        data = json.loads(content)
        info['type'] = type(data).__name__
        
        if isinstance(data, list):
            info['items'] = len(data)
        elif isinstance(data, dict):
            info['keys'] = len(data)
    except json.JSONDecodeError as e:
        return {'valid': False, 'errors': [f'JSON parse error at line {e.lineno}, col {e.colno}: {e.msg}'], 
                'warnings': []}
    
    # Check indentation
    if check_indent is not None:
        lines = content.splitlines()
        indent_errors = []
        for i, line in enumerate(lines, 1):
            if line.strip():
                # Count leading spaces
                leading = len(line) - len(line.lstrip())
                if leading % check_indent != 0:
                    indent_errors.append(i)
        
        if indent_errors:
            warnings.append(f'Lines with incorrect indentation: {indent_errors[:10]}')
    
    # Check if keys are sorted
    if check_sorted and isinstance(data, dict):
        def check_sorted_keys(obj, path=''):
            if isinstance(obj, dict):
                keys = list(obj.keys())
                if keys != sorted(keys):
                    errors.append(f'Keys not sorted at {path or "root"}')
                for key, value in obj.items():
                    check_sorted_keys(value, f'{path}.{key}' if path else key)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    check_sorted_keys(item, f'{path}[{i}]')
        
        check_sorted_keys(data)
    
    # Check for trailing commas (common mistake)
    if ',]' in content.replace(' ', '').replace('\n', '') or \
       ',}' in content.replace(' ', '').replace('\n', ''):
        # This is a heuristic, might have false positives
        pass
    
    valid = len(errors) == 0
    return {'valid': valid, 'errors': errors, 'warnings': warnings, 'info': info}

def validate_yaml(filepath, strict=False, encoding=None):
    """Validate YAML file."""
    enc = encoding or detect_encoding(filepath)
    if not enc:
        return {'valid': False, 'errors': ['Cannot detect encoding'], 'warnings': []}
    
    try:
        with open(filepath, 'r', encoding=enc, errors='replace') as f:
            content = f.read()
    except Exception as e:
        return {'valid': False, 'errors': [str(e)], 'warnings': []}
    
    errors = []
    warnings = []
    info = {}
    
    # Try to import yaml
    try:
        import yaml
    except ImportError:
        warnings.append('PyYAML not installed, using basic validation')
        # Basic validation without PyYAML
        if content.strip():
            # Check for tabs (YAML doesn't allow tabs for indentation)
            lines = content.splitlines()
            for i, line in enumerate(lines, 1):
                if '\t' in line and not line.strip().startswith('#'):
                    errors.append(f'Line {i}: tabs not allowed in YAML indentation')
            
            # Check for consistent indentation
            indent_levels = []
            for i, line in enumerate(lines, 1):
                if line.strip() and not line.strip().startswith('#'):
                    indent = len(line) - len(line.lstrip())
                    indent_levels.append((i, indent))
            
            if indent_levels:
                indents = [x[1] for x in indent_levels]
                if indents and min(indents) > 0:
                    # Check if all indents are multiples of the smallest
                    min_indent = min(indents)
                    for line_num, indent in indent_levels:
                        if indent % min_indent != 0:
                            warnings.append(f'Line {line_num}: inconsistent indentation ({indent} spaces)')
                            break
        
        valid = len(errors) == 0
        return {'valid': valid, 'errors': errors, 'warnings': warnings, 'info': info}
    
    # Parse YAML
    try:
        data = yaml.safe_load(content)
        info['type'] = type(data).__name__ if data else 'empty'
        
        if isinstance(data, dict):
            info['keys'] = len(data)
        elif isinstance(data, list):
            info['items'] = len(data)
    except yaml.YAMLError as e:
        error_msg = str(e)
        if hasattr(e, 'problem_mark'):
            mark = e.problem_mark
            error_msg = f'YAML parse error at line {mark.line + 1}, col {mark.column + 1}: {e.problem}'
        return {'valid': False, 'errors': [error_msg], 'warnings': []}
    
    # Strict checks
    if strict:
        # Check for duplicate keys
        try:
            class DuplicateKeyChecker(yaml.SafeLoader):
                pass
            
            def check_duplicates(loader, node, deep=False):
                mapping = {}
                for key_node, value_node in node.value:
                    key = loader.construct_object(key_node, deep=deep)
                    if key in mapping:
                        raise yaml.MarkError(f'Duplicate key: {key}', key_node.start_mark)
                    mapping[key] = loader.construct_object(value_node, deep=deep)
                return mapping
            
            DuplicateKeyChecker.add_constructor(
                yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
                check_duplicates
            )
            yaml.load(content, Loader=DuplicateKeyChecker)
        except yaml.YAMLError as e:
            errors.append(str(e))
    
    valid = len(errors) == 0
    return {'valid': valid, 'errors': errors, 'warnings': warnings, 'info': info}

def format_result(filepath, result, use_color=True):
    """Format validation result."""
    output = []
    
    output.append(f"File: {filepath}")
    output.append("=" * 60)
    
    if result['valid']:
        if use_color:
            output.append(f"\033[32m✓ Valid\033[0m")
        else:
            output.append("✓ Valid")
    else:
        if use_color:
            output.append(f"\033[31m✗ Invalid\033[0m")
        else:
            output.append("✗ Invalid")
    
    if result.get('info'):
        output.append("\nInfo:")
        for key, value in result['info'].items():
            if key == 'header' and isinstance(value, list):
                output.append(f"  {key}: {', '.join(value[:5])}{'...' if len(value) > 5 else ''}")
            else:
                output.append(f"  {key}: {value}")
    
    if result['errors']:
        output.append("\nErrors:")
        for error in result['errors']:
            if use_color:
                output.append(f"  \033[31m✗\033[0m {error}")
            else:
                output.append(f"  ✗ {error}")
    
    if result['warnings']:
        output.append("\nWarnings:")
        for warning in result['warnings']:
            if use_color:
                output.append(f"  \033[33m⚠\033[0m {warning}")
            else:
                output.append(f"  ⚠ {warning}")
    
    return '\n'.join(output)

def main():
    parser = argparse.ArgumentParser(description='Validate structured text files')
    parser.add_argument('file', help='File to validate')
    parser.add_argument('--format', choices=['csv', 'json', 'yaml'], help='Force format')
    parser.add_argument('--csv-delimiter', help='CSV delimiter')
    parser.add_argument('--csv-strict', action='store_true', help='Strict CSV validation')
    parser.add_argument('--json-indent', type=int, help='Check JSON indentation')
    parser.add_argument('--json-sort-keys', action='store_true', help='Check if JSON keys are sorted')
    parser.add_argument('--yaml-strict', action='store_true', help='Strict YAML validation')
    parser.add_argument('--encoding', help='Force encoding')
    parser.add_argument('--fix', action='store_true', help='Attempt to fix issues')
    parser.add_argument('--json', action='store_true', help='JSON output')
    parser.add_argument('--no-color', action='store_true', help='Disable colors')
    
    args = parser.parse_args()
    
    # Detect format
    fmt = args.format or detect_format(args.file)
    if not fmt:
        print(f"Cannot detect format. Use --format to specify.", file=sys.stderr)
        sys.exit(1)
    
    # Validate
    if fmt == 'csv':
        result = validate_csv(args.file, args.csv_delimiter, args.csv_strict, args.encoding)
    elif fmt == 'json':
        result = validate_json(args.file, args.json_indent, args.json_sort_keys, args.encoding)
    elif fmt == 'yaml':
        result = validate_yaml(args.file, args.yaml_strict, args.encoding)
    else:
        print(f"Unsupported format: {fmt}", file=sys.stderr)
        sys.exit(1)
    
    result['format'] = fmt
    
    # Output
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        use_color = not args.no_color and sys.stdout.isatty()
        print(format_result(args.file, result, use_color))
    
    sys.exit(0 if result['valid'] else 1)

if __name__ == '__main__':
    main()
