#!/usr/bin/env python3
"""
text_encoding.py — Detect and convert file encodings.

Usage:
  python text_encoding.py <command> <file> [options]

Commands:
  detect                 Detect file encoding
  convert                Convert file encoding

Options for detect:
  (no additional options)

Options for convert:
  --from ENC             Source encoding (default: auto-detect)
  --to ENC               Target encoding (default: utf-8)
  -o FILE                Output file (default: overwrite input)
  --add-bom              Add BOM to output
  --remove-bom           Remove BOM from output
  -r, --recursive        Process directories recursively
  --include GLOB         Only process matching files
  --exclude GLOB         Exclude matching files
"""

import argparse
import os
import sys
import fnmatch
import shutil

def detect_encoding(filepath):
    """Detect file encoding with detailed info."""
    info = {
        'file': filepath,
        'encoding': None,
        'has_bom': False,
        'bom_type': None,
        'confidence': 'unknown'
    }
    
    try:
        with open(filepath, 'rb') as f:
            raw = f.read(4)
    except Exception as e:
        info['error'] = str(e)
        return info
    
    # Check BOM
    if raw.startswith(b'\xef\xbb\xbf'):
        info['has_bom'] = True
        info['bom_type'] = 'UTF-8 BOM'
        info['encoding'] = 'utf-8-sig'
        info['confidence'] = 'certain'
        return info
    elif raw[:2] == b'\xff\xfe':
        info['has_bom'] = True
        info['bom_type'] = 'UTF-16 LE BOM'
        info['encoding'] = 'utf-16-le'
        info['confidence'] = 'certain'
        return info
    elif raw[:2] == b'\xfe\xff':
        info['has_bom'] = True
        info['bom_type'] = 'UTF-16 BE BOM'
        info['encoding'] = 'utf-16-be'
        info['confidence'] = 'certain'
        return info
    
    # Try encodings in order of preference
    encodings = [
        ('utf-8', 'high'),
        ('ascii', 'high'),
        ('windows-1251', 'medium'),
        ('windows-1252', 'medium'),
        ('latin-1', 'low'),
        ('cp437', 'low'),
    ]
    
    try:
        with open(filepath, 'rb') as f:
            content = f.read()
    except Exception as e:
        info['error'] = str(e)
        return info
    
    for enc, confidence in encodings:
        try:
            content.decode(enc)
            info['encoding'] = enc
            info['confidence'] = confidence
            return info
        except (UnicodeDecodeError, UnicodeError):
            continue
    
    info['encoding'] = None
    info['confidence'] = 'failed'
    return info

def convert_file(filepath, from_enc=None, to_enc='utf-8', output=None, add_bom=False, remove_bom=False):
    """Convert file encoding."""
    # Detect source encoding if not specified
    if not from_enc:
        det = detect_encoding(filepath)
        from_enc = det['encoding']
        if not from_enc:
            return False, f"Cannot detect encoding for {filepath}"
    
    # Read file
    try:
        with open(filepath, 'rb') as f:
            raw = f.read()
    except Exception as e:
        return False, str(e)
    
    # Remove BOM if present
    if raw.startswith(b'\xef\xbb\xbf'):
        raw = raw[3:]
        if from_enc == 'utf-8-sig':
            from_enc = 'utf-8'
    elif raw.startswith(b'\xff\xfe'):
        raw = raw[2:]
        if from_enc == 'utf-16-le':
            from_enc = 'utf-16'
    elif raw.startswith(b'\xfe\xff'):
        raw = raw[2:]
        if from_enc == 'utf-16-be':
            from_enc = 'utf-16'
    
    # Decode
    try:
        text = raw.decode(from_enc)
    except (UnicodeDecodeError, LookupError) as e:
        return False, f"Cannot decode with {from_enc}: {e}"
    
    # Encode
    target_enc = to_enc
    bom_bytes = b''
    
    if add_bom:
        if to_enc == 'utf-8':
            bom_bytes = b'\xef\xbb\xbf'
            target_enc = 'utf-8'
        elif to_enc == 'utf-16':
            target_enc = 'utf-16'  # Python adds BOM automatically
    
    try:
        encoded = bom_bytes + text.encode(target_enc)
    except (UnicodeEncodeError, LookupError) as e:
        return False, f"Cannot encode with {to_enc}: {e}"
    
    # Write output
    out_path = output or filepath
    try:
        with open(out_path, 'wb') as f:
            f.write(encoded)
    except Exception as e:
        return False, f"Cannot write to {out_path}: {e}"
    
    return True, f"Converted {filepath} from {from_enc} to {to_enc}"

def collect_files(path, recursive=True, include=None, exclude=None):
    """Collect files."""
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

def main():
    parser = argparse.ArgumentParser(description='Detect and convert file encodings')
    parser.add_argument('command', choices=['detect', 'convert'], help='Command')
    parser.add_argument('file', help='File or directory')
    parser.add_argument('--from', dest='from_enc', help='Source encoding')
    parser.add_argument('--to', dest='to_enc', default='utf-8', help='Target encoding')
    parser.add_argument('-o', '--output', help='Output file')
    parser.add_argument('--add-bom', action='store_true', help='Add BOM')
    parser.add_argument('--remove-bom', action='store_true', help='Remove BOM')
    parser.add_argument('-r', '--recursive', action='store_true', help='Recursive')
    parser.add_argument('--include', help='Include glob')
    parser.add_argument('--exclude', help='Exclude glob')
    
    args = parser.parse_args()
    
    if args.command == 'detect':
        files = collect_files(args.file, recursive=args.recursive, 
                             include=args.include, exclude=args.exclude)
        
        for fpath in files:
            info = detect_encoding(fpath)
            if 'error' in info:
                print(f"{fpath}: ERROR - {info['error']}")
            else:
                bom_str = f" (has {info['bom_type']})" if info['has_bom'] else ""
                print(f"{fpath}: {info['encoding']}{bom_str} [{info['confidence']}]")
    
    elif args.command == 'convert':
        files = collect_files(args.file, recursive=args.recursive,
                             include=args.include, exclude=args.exclude)
        
        success = 0
        failed = 0
        for fpath in files:
            ok, msg = convert_file(fpath, args.from_enc, args.to_enc, 
                                    args.output if len(files) == 1 else None,
                                    args.add_bom, args.remove_bom)
            if ok:
                print(msg)
                success += 1
            else:
                print(f"ERROR: {fpath}: {msg}", file=sys.stderr)
                failed += 1
        
        print(f"\nConverted: {success}, Failed: {failed}")

if __name__ == '__main__':
    main()
