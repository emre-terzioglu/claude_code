#!/usr/bin/env python3
"""
fetch_news.py  —  stdlib-only (no pip installs needed)
-------------------------------------------------------
Fetches Google News RSS for three categories and writes data/*.json.
Uses only: urllib, xml.etree.ElementTree, html, json, re, datetime
"""

import html as html_mod
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import quote_plus
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Google News RSS ────────────────────────────────────────────────────────────
GN_RSS = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; InsightsDashboard/1.0; "
        "+https://github.com/emre-terzioglu/claude_code)"
    ),
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
    "Accept-Language": "en-US,en;q=0.9",
}

# ── Category definitions ───────────────────────────────────────────────────────
CATEGORIES = {
    "iot": {
        "label":   "IoT Technologies",
        "queries": [
            "Internet of Things business market 2025",
            "IoT technology industry insights",
            "IoT startup investment funding",
            "edge computing industrial IoT",
        ],
        "output": "data/iot.json",
    },
    "agriculture": {
        "label":   "Predictive Agriculture",
        "queries": [
            "precision agriculture technology market 2025",
            "agtech startup funding investment",
            "predictive agriculture AI machine learning",
            "smart farming sensors drones market",
        ],
        "output": "data/agriculture.json",
    },
    "entrepreneurship": {
        "label":   "Entrepreneurship",
        "queries": [
            "startup funding venture capital 2025",
            "entrepreneurship business innovation news",
            "tech startup growth founder",
            "startup IPO acquisition news",
        ],
        "output": "data/entrepreneurship.json",
    },
}

MAX_PER_QUERY    = 10
MAX_PER_CATEGORY = 25


# ── HTML stripper ──────────────────────────────────────────────────────────────
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
    raw = (raw or "").strip()
    if not raw:
        return ""
    try:
        s = _Stripper()
        s.feed(raw)
        text = s.get_text()
    except Exception:
        text = re.sub(r"<[^>]+>", " ", raw)
    text = html_mod.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ── Date parsing ───────────────────────────────────────────────────────────────
DATE_FMTS = [
    "%a, %d %b %Y %H:%M:%S %z",
    "%a, %d %b %Y %H:%M:%S GMT",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
]


def parse_date(raw: str) -> str | None:
    raw = (raw or "").strip()
    if not raw:
        return None
    # Replace "UT" timezone (non-standard) with "+0000"
    raw = re.sub(r"\bUT\b", "+0000", raw)
    for fmt in DATE_FMTS:
        try:
            dt = datetime.strptime(raw, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).isoformat()
        except ValueError:
            continue
    return raw  # return raw if nothing matched


# ── RSS fetch & parse ──────────────────────────────────────────────────────────
def fetch_rss(url: str, retries: int = 3) -> bytes | None:
    for attempt in range(1, retries + 1):
        try:
            req = Request(url, headers=HEADERS)
            with urlopen(req, timeout=20) as resp:
                return resp.read()
        except (HTTPError, URLError) as exc:
            log.warning("  attempt %d/%d failed: %s", attempt, retries, exc)
            if attempt < retries:
                time.sleep(2 ** attempt)  # 2 s, 4 s back-off
    return None


def parse_rss(xml_bytes: bytes) -> list[dict]:
    """Parse RSS 2.0 XML and return a list of article dicts."""
    articles = []
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        log.error("  XML parse error: %s", exc)
        return []

    # Handle RSS with possible default namespace
    ns_map: dict[str, str] = {}
    # Detect any namespace on root
    m = re.match(r"\{([^}]+)\}", root.tag)
    if m:
        ns_map["rss"] = m.group(1)

    # Walk all <item> elements regardless of namespace
    for item in root.iter("{http://www.w3.org/2005/Atom}entry") or []:
        pass  # Atom fallback — handled below

    items = list(root.iter("item"))
    if not items:
        # Try Atom <entry> elements
        items = list(root.iter("{http://www.w3.org/2005/Atom}entry"))

    for item in items[:MAX_PER_QUERY]:
        title_el = item.find("title")
        link_el  = item.find("link")
        desc_el  = item.find("description")
        date_el  = item.find("pubDate")
        src_el   = item.find("source")

        # Atom fallbacks
        if title_el is None:
            title_el = item.find("{http://www.w3.org/2005/Atom}title")
        if link_el is None:
            link_el  = item.find("{http://www.w3.org/2005/Atom}link")
        if date_el is None:
            date_el  = item.find("{http://www.w3.org/2005/Atom}published")
            if date_el is None:
                date_el = item.find("{http://www.w3.org/2005/Atom}updated")

        title = strip_html(title_el.text if title_el is not None else "")

        # Link can be text or href attribute (Atom)
        link = ""
        if link_el is not None:
            link = (link_el.text or link_el.get("href", "")).strip()

        # Fallback to <guid> if link is empty
        if not link:
            guid_el = item.find("guid")
            if guid_el is not None and (guid_el.text or "").startswith("http"):
                link = guid_el.text.strip()

        if not title or not link:
            continue

        description = strip_html(desc_el.text if desc_el is not None else "")[:500]
        pub_date    = parse_date(date_el.text if date_el is not None else "")
        source      = strip_html(src_el.text  if src_el  is not None else "")

        articles.append({
            "title":       title,
            "link":        link,
            "description": description,
            "pub_date":    pub_date,
            "source":      source,
        })

    return articles


# ── Category fetcher ───────────────────────────────────────────────────────────
def fetch_category(info: dict) -> list[dict]:
    seen_links:  set[str] = set()
    seen_titles: set[str] = set()
    all_articles: list[dict] = []

    for query in info["queries"]:
        url = GN_RSS.format(query=quote_plus(query))
        log.info("  ↳ %s", query)
        xml_bytes = fetch_rss(url)
        if not xml_bytes:
            log.warning("    No data returned, skipping.")
            continue

        for art in parse_rss(xml_bytes):
            lk = art["link"]
            tk = art["title"].lower()[:60]
            if lk in seen_links or tk in seen_titles:
                continue
            seen_links.add(lk)
            seen_titles.add(tk)
            all_articles.append(art)

    # Newest first
    all_articles.sort(key=lambda x: x.get("pub_date") or "", reverse=True)
    return all_articles[:MAX_PER_CATEGORY]


# ── Main ───────────────────────────────────────────────────────────────────────
def main() -> None:
    os.makedirs("data", exist_ok=True)
    now_iso   = datetime.now(timezone.utc).isoformat()
    any_error = False

    for key, info in CATEGORIES.items():
        log.info("━━ [%s] %s", key, info["label"])
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

        log.info("  ✓ %d articles saved → %s", len(articles), info["output"])

    if any_error:
        sys.exit(1)
    log.info("All done.")


if __name__ == "__main__":
    main()
