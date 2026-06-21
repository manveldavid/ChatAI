#!/usr/bin/env python3
"""
text_check.py — Check text file formatting and encoding.

Usage:
  python text_check.py <file> [options]

Options:
  --encoding ENC         Expected encoding (default: utf-8)
  --check-bom            Check for BOM presence
  --check-eol            Check line endings (CRLF/LF)
  --check-trailing       Check for trailing whitespace
  --check-tabs           Check for tabs (vs spaces)
  --check-empty-lines    Check for multiple empty lines
  --check-final-newline  Check if file ends with newline
  --all                  Run all checks
  --json                 Output as JSON
"""

import argparse
import sys
import json

def detect_encoding(filepath):
    """Detect actual file encoding."""
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

def check_file(filepath, expected_encoding='utf-8', checks=None):
    """Run formatting checks on file."""
    if checks is None:
        checks = {}
    
    results = {
        'file': filepath,
        'checks': {},
        'warnings': [],
        'errors': []
    }
    
    # Read raw bytes for binary checks
    try:
        with open(filepath, 'rb') as f:
            raw_content = f.read()
    except Exception as e:
        results['errors'].append(f"Cannot read file: {e}")
        return results
    
    # Encoding check
    if checks.get('encoding', True):
        actual_encoding = detect_encoding(filepath)
        results['checks']['encoding'] = {
            'expected': expected_encoding,
            'actual': actual_encoding,
            'passed': actual_encoding == expected_encoding or actual_encoding == expected_encoding + '-sig'
        }
        if not results['checks']['encoding']['passed']:
            results['warnings'].append(f"Encoding mismatch: expected {expected_encoding}, got {actual_encoding}")
    
    # BOM check
    if checks.get('bom', False):
        has_bom = raw_content.startswith(b'\xef\xbb\xbf')
        results['checks']['bom'] = {
            'has_bom': has_bom,
            'passed': not has_bom  # Usually BOM is not desired
        }
        if has_bom:
            results['warnings'].append("File has UTF-8 BOM")
    
    # Decode for text checks
    enc = actual_encoding or 'utf-8'
    try:
        content = raw_content.decode(enc)
    except:
        content = raw_content.decode('utf-8', errors='replace')
    
    lines = content.split('\n')
    
    # Line endings check
    if checks.get('eol', True):
        has_crlf = b'\r\n' in raw_content
        has_lf = b'\n' in raw_content and not has_crlf
        eol_type = 'CRLF' if has_crlf else 'LF'
        results['checks']['eol'] = {
            'type': eol_type,
            'consistent': not (has_crlf and has_lf)
        }
        if not results['checks']['eol']['consistent']:
            results['warnings'].append("Mixed line endings detected")
    
    # Trailing whitespace check
    if checks.get('trailing', True):
        trailing_lines = []
        for i, line in enumerate(lines, 1):
            if line.rstrip('\r') != line.rstrip('\r').rstrip():
                trailing_lines.append(i)
        
        results['checks']['trailing_whitespace'] = {
            'count': len(trailing_lines),
            'lines': trailing_lines[:10],  # First 10
            'passed': len(trailing_lines) == 0
        }
        if trailing_lines:
            results['warnings'].append(f"Found {len(trailing_lines)} lines with trailing whitespace")
    
    # Tabs check
    if checks.get('tabs', False):
        tab_lines = []
        for i, line in enumerate(lines, 1):
            if '\t' in line:
                tab_lines.append(i)
        
        results['checks']['tabs'] = {
            'count': len(tab_lines),
            'lines': tab_lines[:10],
            'passed': len(tab_lines) == 0
        }
        if tab_lines:
            results['warnings'].append(f"Found {len(tab_lines)} lines with tabs")
    
    # Multiple empty lines check
    if checks.get('empty_lines', False):
        consecutive_empty = []
        empty_count = 0
        for i, line in enumerate(lines, 1):
            if line.strip() == '':
                empty_count += 1
                if empty_count >= 2:
                    consecutive_empty.append(i)
            else:
                empty_count = 0
        
        results['checks']['multiple_empty_lines'] = {
            'count': len(consecutive_empty),
            'lines': consecutive_empty[:10],
            'passed': len(consecutive_empty) == 0
        }
        if consecutive_empty:
            results['warnings'].append(f"Found {len(consecutive_empty)} places with multiple empty lines")
    
    # Final newline check
    if checks.get('final_newline', True):
        ends_with_newline = content.endswith('\n')
        results['checks']['final_newline'] = {
            'present': ends_with_newline,
            'passed': ends_with_newline
        }
        if not ends_with_newline:
            results['warnings'].append("File does not end with newline")
    
    # Summary
    results['summary'] = {
        'total_checks': len(results['checks']),
        'passed': sum(1 for c in results['checks'].values() if c.get('passed', True)),
        'failed': sum(1 for c in results['checks'].values() if not c.get('passed', True)),
        'warnings': len(results['warnings'])
    }
    
    return results

def format_results(results, use_color=True):
    """Format check results for display."""
    output = []
    
    output.append(f"File: {results['file']}")
    output.append("=" * 60)
    
    for check_name, check_data in results['checks'].items():
        passed = check_data.get('passed', True)
        status = "✓" if passed else "✗"
        
        if use_color:
            if passed:
                status_str = f"\033[32m{status}\033[0m"
            else:
                status_str = f"\033[31m{status}\033[0m"
        else:
            status_str = status
        
        output.append(f"{status_str} {check_name}")
        
        # Show details
        for key, value in check_data.items():
            if key != 'passed' and key != 'lines':
                output.append(f"    {key}: {value}")
        
        if 'lines' in check_data and check_data['lines']:
            lines_str = ', '.join(map(str, check_data['lines'][:5]))
            if len(check_data['lines']) > 5:
                lines_str += f" ... (+{len(check_data['lines']) - 5} more)"
            output.append(f"    lines: {lines_str}")
    
    output.append("=" * 60)
    output.append(f"Summary: {results['summary']['passed']}/{results['summary']['total_checks']} checks passed")
    
    if results['warnings']:
        output.append("\nWarnings:")
        for warning in results['warnings']:
            output.append(f"  ⚠ {warning}")
    
    return '\n'.join(output)

def main():
    parser = argparse.ArgumentParser(description='Check text file formatting')
    parser.add_argument('file', help='File to check')
    parser.add_argument('--encoding', default='utf-8', help='Expected encoding')
    parser.add_argument('--check-bom', action='store_true', help='Check for BOM')
    parser.add_argument('--check-eol', action='store_true', help='Check line endings')
    parser.add_argument('--check-trailing', action='store_true', help='Check trailing whitespace')
    parser.add_argument('--check-tabs', action='store_true', help='Check for tabs')
    parser.add_argument('--check-empty-lines', action='store_true', help='Check multiple empty lines')
    parser.add_argument('--check-final-newline', action='store_true', help='Check final newline')
    parser.add_argument('--all', action='store_true', help='Run all checks')
    parser.add_argument('--json', action='store_true', help='JSON output')
    parser.add_argument('--no-color', action='store_true', help='Disable colors')
    
    args = parser.parse_args()
    
    # Determine which checks to run
    checks = {
        'encoding': True,
        'eol': True,
        'trailing': True,
        'final_newline': True
    }
    
    if args.all:
        checks = {
            'encoding': True,
            'bom': True,
            'eol': True,
            'trailing': True,
            'tabs': True,
            'empty_lines': True,
            'final_newline': True
        }
    else:
        if args.check_bom:
            checks['bom'] = True
        if args.check_eol:
            checks['eol'] = True
        if args.check_trailing:
            checks['trailing'] = True
        if args.check_tabs:
            checks['tabs'] = True
        if args.check_empty_lines:
            checks['empty_lines'] = True
        if args.check_final_newline:
            checks['final_newline'] = True
    
    # Run checks
    results = check_file(args.file, args.encoding, checks)
    
    # Output
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        use_color = not args.no_color and sys.stdout.isatty()
        print(format_results(results, use_color))
    
    # Exit code
    sys.exit(0 if results['summary']['failed'] == 0 else 1)

if __name__ == '__main__':
    main()
