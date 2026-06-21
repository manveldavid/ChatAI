# DuckDuckGo Search - API Reference

## Library: duckduckgo-search

### Installation
```bash
pip install duckduckgo-search
```

### DDGS - Main Class

Create instance with context manager for proper resource management:
```python
from duckduckgo_search import DDGS

with DDGS() as ddgs:
    results = ddgs.text("query", max_results=10)
```

### Search Methods

#### 1. `ddgs.text(query, **kwargs)` - Web Search
Search the web for general information.

**Parameters:**
- `query` (str): Search query
- `region` (str): Region code (wt-wt, us-en, uk-en, ru-ru, etc.)
- `safesearch` (str): moderate, on, off
- `timelimit` (str): d (day), w (week), m (month), y (year)
- `max_results` (int): Maximum results to return

**Returns:** Iterator of dicts with keys: title, href, body

#### 2. `ddgs.news(query, **kwargs)` - News Search
Search for news articles.

**Parameters:**
- `query` (str): News search query
- `region` (str): Region code
- `safesearch` (str): moderate, on, off
- `timelimit` (str): d, w, m
- `max_results` (int): Maximum results

**Returns:** Iterator of dicts with keys: title, url, source, date, body

#### 3. `ddgs.images(query, **kwargs)` - Image Search
Search for images.

**Parameters:**
- `query` (str): Image search query
- `region` (str): Region code
- `safesearch` (str): moderate, on, off
- `timelimit` (str): d, w, m, y
- `size` (str): Small, Medium, Large, Wallpaper
- `color` (str): color, Monochrome, etc.
- `type_image` (str): photo, clipart, gif, transparent, line
- `layout` (str): Square, Tall, Wide
- `max_results` (int): Maximum results

**Returns:** Iterator of dicts with keys: title, image, source, thumbnail

#### 4. `ddgs.videos(query, **kwargs)` - Video Search
Search for videos.

**Parameters:**
- `query` (str): Video search query
- `region` (str): Region code
- `safesearch` (str): moderate, on, off
- `timelimit` (str): d, w, m
- `resolution` (str): high, medium
- `duration` (str): short, medium, long
- `max_results` (int): Maximum results

**Returns:** Iterator of dicts with keys: title, description, url, duration, views, published, publisher

### Region Codes

Common region codes:
- `wt-wt` - World
- `us-en` - United States
- `uk-en` - United Kingdom
- `ru-ru` - Russia
- `de-de` - Germany
- `fr-fr` - France
- `es-es` - Spain

### Error Handling

The library may raise:
- `DuckDuckGoSearchException`: General search error
- `TimeoutException`: Request timed out
- `httpx.RequestError`: Network issues

### Best Practices

1. Always use `with DDGS() as ddgs:` context manager
2. Set reasonable max_results (5-20 typically)
3. Use region codes for localized results
4. Handle exceptions gracefully
5. For fresh news, use timelimit='d' or 'w'
