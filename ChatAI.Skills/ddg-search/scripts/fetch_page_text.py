#!/usr/bin/env python3
"""HTML page text extractor — extracts visible text and links from a web page.

Usage:
    python fetch_page_text.py <url> [timeout_seconds]

Returns JSON with visible text and links found on the page.
Uses only Python standard library (urllib, html.parser, json).
"""

import sys
import json
import urllib.request
import urllib.error
from html.parser import HTMLParser

# Tags whose content should be completely ignored (not visible to user)
IGNORED_TAGS = {
    'script', 'style', 'noscript', 'iframe', 'object', 'embed',
    'svg', 'math', 'template', 'meta', 'link', 'head',
}

# Tags that are invisible by default via CSS but still in body
HIDDEN_TAGS = {'br', 'hr'}


class VisibleTextParser(HTMLParser):
    """Parser that extracts visible text and links from HTML."""

    def __init__(self):
        super().__init__()
        self._ignore_depth = 0          # depth inside ignored tags
        self._text_parts = []           # list of text strings
        self._links = []                # list of {"text": ..., "url": ...}
        self._in_anchor = False         # currently inside <a> tag
        self._anchor_text = ''          # accumulated text inside <a>
        self._href = ''                 # href of current <a>
        self._pending_anchor_text = ''

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)

        if self._ignore_depth > 0:
            return

        tag_lower = tag.lower()

        if tag_lower in IGNORED_TAGS:
            self._ignore_depth += 1
            return

        # Track anchor tags to associate text with links
        if tag_lower == 'a' and 'href' in attrs_dict:
            href = attrs_dict['href']
            # Skip javascript: and anchor-only links
            if href and not href.startswith('javascript:') and not (href.startswith('#') and len(href) <= 1):
                self._in_anchor = True
                self._anchor_text = ''
                self._href = href

    def handle_endtag(self, tag):
        tag_lower = tag.lower()

        if self._ignore_depth > 0:
            if tag_lower in IGNORED_TAGS:
                self._ignore_depth -= 1
            return

        if tag_lower == 'a' and self._in_anchor:
            text = self._anchor_text.strip()
            href = self._href
            if text and href:
                self._links.append({"text": text, "url": href})
            self._in_anchor = False
            self._anchor_text = ''
            self._href = ''

        # Add structural line breaks for readability
        if tag_lower in ('p', 'div', 'li', 'tr', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                         'section', 'article', 'header', 'footer', 'nav', 'main',
                         'blockquote', 'pre', 'figure', 'table', 'form', 'details',
                         'dl', 'ul', 'ol', 'br', 'hr'):
            self._text_parts.append('\n')

    def handle_data(self, data):
        if self._ignore_depth > 0:
            return

        # Clean up whitespace but preserve meaningful spacing
        cleaned = data.replace('\t', ' ').replace('\r', '')
        if not cleaned.strip():
            return

        if self._in_anchor:
            self._anchor_text += cleaned
        else:
            self._text_parts.append(cleaned)

    def handle_entityref(self, name):
        if self._ignore_depth > 0:
            return
        # Basic entity handling
        entities = {'nbsp': ' ', 'amp': '&', 'lt': '<', 'gt': '>', 'quot': '"', 'apos': "'"}
        char = entities.get(name, f'&{name};')
        if self._in_anchor:
            self._anchor_text += char
        else:
            self._text_parts.append(char)

    def handle_charref(self, name):
        if self._ignore_depth > 0:
            return
        try:
            if name.startswith('x'):
                char = chr(int(name[1:], 16))
            else:
                char = chr(int(name))
        except (ValueError, OverflowError):
            return
        if self._in_anchor:
            self._anchor_text += char
        else:
            self._text_parts.append(char)

    def get_text(self) -> str:
        result = ''.join(self._text_parts)
        # Collapse excessive whitespace
        lines = result.split('\n')
        cleaned_lines = []
        for line in lines:
            # Collapse multiple spaces into one
            import re
            line = re.sub(r'[\x20]+', ' ', line).strip()
            if line or cleaned_lines:
                cleaned_lines.append(line)
        # Collapse multiple blank lines into one
        final_lines = []
        prev_blank = False
        for line in cleaned_lines:
            if not line:
                if not prev_blank:
                    final_lines.append('')
                prev_blank = True
            else:
                final_lines.append(line)
                prev_blank = False
        return '\n'.join(final_lines).strip()

    def get_links(self) -> list:
        return self._links


def fetch_page(url: str, timeout: int = 15) -> str:
    """Fetch HTML content from a URL."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'identity',
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        # Try to detect encoding
        content_type = response.headers.get('Content-Type', '')
        encoding = 'utf-8'
        if 'charset=' in content_type:
            encoding = content_type.split('charset=')[-1].split(';')[0].strip()
        raw = response.read()
        try:
            return raw.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            return raw.decode('utf-8', errors='replace')


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"success": False, "error": "Usage: fetch_page_text.py <url> [timeout_seconds]"}))
        sys.exit(1)

    url = sys.argv[1]
    timeout = int(sys.argv[2]) if len(sys.argv) > 2 else 15

    try:
        html = fetch_page(url, timeout)
    except urllib.error.URLError as e:
        print(json.dumps({"success": False, "error": f"Failed to fetch URL: {str(e)}"}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"success": False, "error": f"Error fetching page: {str(e)}"}))
        sys.exit(1)

    parser = VisibleTextParser()
    try:
        parser.feed(html)
    except Exception as e:
        print(json.dumps({"success": False, "error": f"Error parsing HTML: {str(e)}"}))
        sys.exit(1)

    visible_text = parser.get_text()
    links = parser.get_links()

    result = {
        "success": True,
        "url": url,
        "text": visible_text,
        "links": links,
        "link_count": len(links),
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
