"""
DuckDuckGo News Search Script — zero dependencies (stdlib only).

Usage: python news_search.py <query> [max_results] [region] [timelimit]

  query        News topic
  max_results  Maximum results (default: 8)
  region       Region code (default: us-en)
  timelimit    Time filter: d (day), w (week), m (month) — default: d

Outputs JSON to stdout.  No third-party packages required.
"""

import sys
import json
import re
import urllib.request
import urllib.parse
import http.cookiejar
import ssl

# Reuse same opener / headers as search.py

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) "
        "Gecko/20100101 Firefox/115.0"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "identity",
    "DNT": "1",
    "Connection": "keep-alive",
}

_opener = None

def _get_opener():
    global _opener
    if _opener is None:
        ctx = ssl.create_default_context()
        cj = http.cookiejar.CookieJar()
        _opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(cj),
            urllib.request.HTTPSHandler(context=ctx),
        )
    return _opener


def _unwrap(ddg_url: str) -> str:
    ddg_url = ddg_url.replace("&amp;", "&")
    if "uddg=" in ddg_url:
        start = ddg_url.index("uddg=") + 5
        amp = ddg_url.find("&", start)
        encoded = ddg_url[start:] if amp == -1 else ddg_url[start:amp]
        return urllib.parse.unquote(encoded)
    return ddg_url


def _strip(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).strip()


def _hostname(url: str) -> str:
    try:
        p = urllib.parse.urlparse(url)
        host = p.hostname or ""
        if host.startswith("www."):
            host = host[4:]
        return host
    except Exception:
        return ""


def search(query: str, max_results: int = 8,
           region: str = "us-en", timelimit: str = "d") -> dict:
    """Search for recent news via DuckDuckGo HTML.

    Uses a time filter (default past day) to prioritise fresh articles.
    """
    try:
        params = {"q": query, "kl": region}
        if timelimit:
            params["df"] = timelimit
        url = ("https://html.duckduckgo.com/html/?"
               + urllib.parse.urlencode(params))
        req = urllib.request.Request(url, headers=_HEADERS)
        with _get_opener().open(req, timeout=20) as resp:
            html = resp.read().decode("utf-8")
    except Exception as exc:
        return {"success": False, "error": str(exc)}

    links_pos = html.find('id="links"')
    if links_pos == -1:
        return {"success": True, "query": query, "count": 0,
                "results": [], "message": "No news results found"}

    section = html[links_pos:]
    end = len(section)
    for marker in ('class="nav-link', 'class="feedback'):
        i = section.find(marker)
        if i != -1 and i < end:
            end = i
    content = section[:end]

    blocks = content.split('<div class="result ')
    results: list[dict] = []

    for block in blocks[1:]:
        head = block[:200]
        if "result--ad" in head and "result--ad--" not in head:
            continue

        title_m = re.search(r'class="result__a"[^>]*>(.*?)</a>', block, re.DOTALL)
        if not title_m:
            continue

        url_m = re.search(r'class="result__a"[^>]*href="([^"]*)"', block)
        ddg_url = url_m.group(1) if url_m else ""
        real_url = _unwrap(ddg_url)

        # Source from result__url span or hostname
        source = ""
        url_src = re.search(r'class="result__url"[^>]*>(.*?)<', block, re.DOTALL)
        if url_src:
            source = _strip(url_src.group(1))
            # Clean up source - if it's a URL, extract hostname
            if source.startswith("http"):
                source = _hostname(source)
            elif "/" in source:
                source = source.split("/")[0]
        if not source and real_url:
            source = _hostname(real_url)

        snippet_m = re.search(r'class="result__snippet"[^>]*>(.*?)</a>',
                              block, re.DOTALL)
        snippet = _strip(snippet_m.group(1)) if snippet_m else ""

        results.append({
            "title": _strip(title_m.group(1)),
            "url": real_url,
            "source": source,
            "snippet": snippet,
        })

        if len(results) >= max_results:
            break

    return {"success": True, "query": query,
            "count": len(results), "results": results}


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"success": False,
                          "error": "Usage: python news_search.py <query> [max_results] [region] [timelimit]"}))
        sys.exit(1)

    query = sys.argv[1]
    max_results = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    region = sys.argv[3] if len(sys.argv) > 3 else "us-en"
    timelimit = sys.argv[4] if len(sys.argv) > 4 else "d"

    print(json.dumps(search(query, max_results, region, timelimit),
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
