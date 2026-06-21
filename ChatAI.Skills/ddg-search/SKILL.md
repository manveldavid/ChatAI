---
name: ddg-search
description: Search the internet using DuckDuckGo. Use this skill whenever the user wants to search the web, find information online, look up news, search for images, or get current/recent information that might not be in my training data. Always trigger when the user mentions: web search, internet search, search online, find information, look up, search for news, search images, or asks questions about current events or recent information.
---

# DuckDuckGo Search

Search the internet using DuckDuckGo's HTML interface. Zero external dependencies — uses only Python standard library (`urllib`, `json`, `re`).

## When to Use

Use this skill whenever you need to:
- Search the web for information, articles, or facts
- Find current/recent news
- Look up specific details that may be time-sensitive
- Get information beyond your training data

## Search Workflow (пошаговый алгоритм)

Всегда следуйте этой последовательности при поиске информации:

### Шаг 1: Поиск релевантных ссылок
Выполните поиск через `search.py` или `news_search.py`, чтобы получить список релевантных URL. Запросите достаточное количество результатов (10–15). Результат — список ссылок с заголовками и сниппетами.

### Шаг 2: Парсинг первой ссылки
Возьмите первую ссылку из результатов и извлеките текст страницы через `fetch_page_text.py`:

### Шаг 3: Анализ извлечённого текста
Внимательно прочитайте полученный текст. Определите:
- Содержит ли он релевантную информацию по запросу пользователя?
- Являются ли факты правдивыми и достоверными?
- Достаточно ли информации для полного ответа?

### Шаг 4: Принятие решения

**Если информация исчерпывающая и факты правдивы:**
- Прекратите поиск.
- Сформируйте ответ на основе найденной информации.
- Обязательно укажите источник (URL).

**Если информации недостаточно:**
- Перейдите к следующей ссылке из результатов поиска (Шаг 2 для следующей ссылки).
- Парсите её и анализируйте аналогично.

**Если все ссылки из текущего поиска обработаны, но информации всё ещё недостаточно:**
- Выполните **новый поисковый запрос** с увеличенным количеством результатов (например, 20–25).
- Можно также переформулировать запрос или использовать другой поисковый скрипт (web → news или наоборот).
- Продолжайте цикл: поиск → парсинг → анализ.

### Шаг 5: Формирование ответа
Когда достаточно информации собрано:
- Представьте ответ в структурированном виде.
- Цитируйте источники, указывая URL.
- Если данные из нескольких источников — объедините и сопоставьте их.

## Search Scripts

### Web Search (`scripts/search.py`)
General information, articles, documentation, websites.

**When to use:** User asks "what is...", "how to...", "find information about...", "search for..."

Optional args: `region` (e.g. `ru-ru` for Russian, `us-en` for US), `timelimit` (`d`, `w`, `m`, `y`)

### News Search (`scripts/news_search.py`)
Recent news and current events. Prioritises fresh results using a time filter.

**When to use:** User asks about current events, "latest news on...", "what happened today...", mentions "news", "recent", "latest"

Optional args: `region`, `timelimit` (default: `d` for past day)

## Script Output Format

Both scripts return JSON to stdout:

**Success:**
```json
{
  "success": true,
  "query": "search query",
  "count": 5,
  "results": [
    {
      "title": "Page Title",
      "url": "https://example.com/...",
      "snippet": "Brief excerpt from the page..."
    }
  ]
}
```

**News adds `source` field:**
```json
"results": [
  {"title": "...", "url": "...", "source": "reuters.com", "snippet": "..."}
]
```

**Error:**
```json
{"success": false, "error": "description of what went wrong"}
```

## Fetch Page Text (`scripts/fetch_page_text.py`)

Extract visible text and links from any web page.

**Returns JSON:**
```json
{
  "success": true,
  "url": "https://example.com",
  "text": "Visible text as user would see it...",
  "links": [
    {"text": "Link text", "url": "https://..."},
    {"text": "Another link", "url": "https://..."}
  ],
  "link_count": 2
}
```

**What it does:**
- Removes all `<script>`, `<style>`, `<meta>`, `<noscript>`, `<iframe>`, `<svg>`, `<head>` content
- Preserves visible text with structural line breaks
- Collects all anchor (`<a>`) links with their display text and href
- Uses a realistic browser User-Agent for compatibility

## Tips

- Default region is `us-en`; use `ru-ru` for Russian results, etc.
- If results are sparse, try adjusting the `region` or broadening the query
- For news, the default time filter is past day — widen to `w` (week) if limited

## Error Handling

- If `success` is `false`, describe the error and retry with a simpler query
- Common errors: network timeout, HTTP error from DuckDuckGo
- If no results are found, suggest alternative search terms


<scripts>
  <script name="scripts/search.py">
    <parameters_schema>{"type":"array","items":{"type":"string"}}</parameters_schema>
  </script>
  <script name="scripts/news_search.py">
    <parameters_schema>{"type":"array","items":{"type":"string"}}</parameters_schema>
  </script>
  <script name="scripts/fetch_page_text.py">
    <parameters_schema>{"type":"array","items":{"type":"string"}}</parameters_schema>
  </script>
</scripts>