#!/usr/bin/env python3
"""
fetch_news.py
-------------
Fetches latest news from Google News RSS for three categories:
  • IoT Technologies (business & market insights)
  • Predictive Agriculture (agtech & precision farming)
  • Entrepreneurship (startups, VC, founder news)

Writes results to data/*.json for the dashboard to consume.
Adapted from the existing morning_briefing/news_fetcher.py pattern.
"""

import calendar
import html
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import quote_plus

import feedparser

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Google News RSS base URL ──────────────────────────────────────────────────
GN_RSS = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"

# ── Search queries per category (multiple for broader coverage) ────────────────
CATEGORIES = {
    "iot": {
        "label":   "IoT Technologies",
        "queries": [
            "Internet of Things business market 2024 2025",
            "IoT technology industry insights",
            "IoT startup investment funding",
            "edge computing IoT enterprise",
            "smart devices industrial IoT",
        ],
        "output": "data/iot.json",
    },
    "agriculture": {
        "label":   "Predictive Agriculture",
        "queries": [
            "precision agriculture technology market",
            "agtech startup funding investment",
            "predictive agriculture AI machine learning",
            "smart farming IoT sensors drones",
            "agricultural technology market growth",
        ],
        "output": "data/agriculture.json",
    },
    "entrepreneurship": {
        "label":   "Entrepreneurship",
        "queries": [
            "startup funding venture capital 2024 2025",
            "entrepreneurship business innovation",
            "startup ecosystem growth founder",
            "tech startup IPO acquisition news",
            "small business entrepreneur success",
        ],
        "output": "data/entrepreneurship.json",
    },
}

MAX_PER_QUERY    = 8   # articles per query
MAX_PER_CATEGORY = 25  # total articles per category (after dedup)
BOT_AGENT        = "InsightsDashboard/1.0 (github-actions)"


# ── HTML stripping ────────────────────────────────────────────────────────────

class _Stripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.convert_charrefs = True
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self._parts.append(data)

    def get_text(self) -> str:
        return " ".join(self._parts).strip()


def strip_html(raw: str) -> str:
    raw = raw or ""
    try:
        s = _Stripper()
        s.feed(raw)
        text = s.get_text()
    except Exception:
        text = re.sub(r"<[^>]+>", " ", raw)
    # collapse whitespace and unescape entities
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ── Feedparser helpers ────────────────────────────────────────────────────────

def _pub_iso(entry) -> str | None:
    """Convert feedparser's struct_time to ISO-8601 string (UTC)."""
    pub = entry.get("published_parsed")
    if pub is None:
        return None
    dt = datetime.fromtimestamp(calendar.timegm(pub), tz=timezone.utc)
    return dt.isoformat()


def _parse_entry(entry) -> dict | None:
    title = strip_html(entry.get("title", "")).strip()
    link  = entry.get("link", "").strip()
    if not title or not link:
        return None

    description = strip_html(entry.get("summary", ""))[:600]
    source      = ""

    # Google News puts source name in <source> tag inside the entry
    src_tag = entry.get("source", {})
    if isinstance(src_tag, dict):
        source = src_tag.get("title", "")
    elif isinstance(src_tag, str):
        source = src_tag

    return {
        "title":       title,
        "link":        link,
        "description": description,
        "pub_date":    _pub_iso(entry),
        "source":      strip_html(source),
    }


# ── Fetch one query ───────────────────────────────────────────────────────────

def fetch_query(query: str) -> list[dict]:
    url = GN_RSS.format(query=quote_plus(query))
    log.debug("  GET %s", url)
    try:
        feed = feedparser.parse(url, agent=BOT_AGENT)
    except Exception as exc:
        log.error("  feedparser error: %s", exc)
        return []

    if feed.bozo and feed.bozo_exception:
        log.warning("  parse warning: %s", feed.bozo_exception)

    results = []
    for entry in feed.entries[:MAX_PER_QUERY]:
        try:
            art = _parse_entry(entry)
            if art:
                results.append(art)
        except Exception as exc:
            log.warning("  skipped entry: %s", exc)

    log.info("  %-50s → %d articles", f"'{query[:48]}'", len(results))
    return results


# ── Fetch one category ────────────────────────────────────────────────────────

def fetch_category(info: dict) -> list[dict]:
    seen_links: set[str] = set()
    seen_titles: set[str] = set()
    all_articles: list[dict] = []

    for query in info["queries"]:
        for art in fetch_query(query):
            link_key  = art["link"]
            title_key = art["title"].lower()[:60]
            if link_key in seen_links or title_key in seen_titles:
                continue
            seen_links.add(link_key)
            seen_titles.add(title_key)
            all_articles.append(art)

    # Sort newest first
    all_articles.sort(key=lambda x: x.get("pub_date") or "", reverse=True)
    return all_articles[:MAX_PER_CATEGORY]


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    os.makedirs("data", exist_ok=True)
    now_iso = datetime.now(timezone.utc).isoformat()
    any_error = False

    for key, info in CATEGORIES.items():
        log.info("━━ Fetching category: %s", info["label"])
        try:
            articles = fetch_category(info)
        except Exception as exc:
            log.error("Category '%s' failed: %s", key, exc)
            articles = []
            any_error = True

        payload = {
            "category":   info["label"],
            "updated_at": now_iso,
            "count":      len(articles),
            "articles":   articles,
        }

        with open(info["output"], "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        log.info("  ✓ Saved %d articles → %s", len(articles), info["output"])

    if any_error:
        sys.exit(1)
    log.info("Done.")


if __name__ == "__main__":
    main()
