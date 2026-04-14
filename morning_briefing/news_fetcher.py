"""
Fetches articles from Google News RSS feeds for the three target domains:
  - Startup ecosystem / venture capital
  - Precision agriculture / AgTech
  - IoT / Edge AI

Returns articles published in the last 24 hours.
"""

import calendar
import logging
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from urllib.parse import quote_plus

import feedparser

logger = logging.getLogger(__name__)

QUERIES = [
    "startup funding OR venture capital",
    "precision agriculture OR agtech",
    "IoT OR edge AI",
]

RSS_URL = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"


class _HTMLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.convert_charrefs = True
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self._parts.append(data)

    def get_text(self) -> str:
        return " ".join(self._parts).strip()


def _strip_html(raw: str) -> str:
    s = _HTMLStripper()
    try:
        s.feed(raw)
        return s.get_text()
    except Exception:
        return raw


def _parse_entry(entry, cutoff: datetime, query: str) -> dict | None:
    """Parse a feedparser entry into a clean dict. Returns None if too old or unparseable."""
    pub = entry.get("published_parsed")
    if pub is None:
        return None

    # calendar.timegm treats struct_time as UTC (correct for Google News RSS)
    published = datetime.fromtimestamp(calendar.timegm(pub), tz=timezone.utc)
    if published < cutoff:
        return None

    title = _strip_html(entry.get("title", "")).strip()
    if not title:
        return None

    return {
        "title": title,
        "link": entry.get("link", ""),
        "date": published,
        "description": _strip_html(entry.get("summary", ""))[:600],
        "source_query": query,
    }


def _fetch_query(query: str, cutoff: datetime) -> list[dict]:
    url = RSS_URL.format(query=quote_plus(query))
    logger.debug("Fetching RSS: %s", url)

    try:
        feed = feedparser.parse(url, agent="MorningBriefingBot/1.0")
    except Exception as exc:
        logger.error("feedparser error for '%s': %s", query, exc)
        return []

    if feed.bozo and feed.bozo_exception:
        logger.warning("Feed parse warning for '%s': %s", query, feed.bozo_exception)

    results = []
    for entry in feed.entries:
        try:
            article = _parse_entry(entry, cutoff, query)
            if article:
                results.append(article)
        except Exception as exc:
            logger.warning("Skipping malformed entry: %s", exc)

    logger.info("'%s' -> %d articles in last 24h", query, len(results))
    return results


def fetch_all_articles() -> list[dict]:
    """Fetch articles from all configured queries. Returns a flat list."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    all_articles: list[dict] = []
    for query in QUERIES:
        all_articles.extend(_fetch_query(query, cutoff))
    logger.info("Total raw articles fetched: %d", len(all_articles))
    return all_articles
