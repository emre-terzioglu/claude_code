"""
Deduplicates, scores, and ranks articles.

Scoring weights:
  +3  AgTech / precision agriculture keywords
  +2  IoT / Edge AI keywords
  +2  Startup / funding / VC keywords

Only articles with score > 0 advance. Top N returned.
"""

import logging
import re

logger = logging.getLogger(__name__)

# (keyword_list, score_delta)
SCORING_RULES: list[tuple[list[str], int]] = [
    (
        [
            "agtech", "precision agriculture", "precision farming", "smart farming",
            "crop yield", "soil sensor", "farm management", "harvest", "fertilizer",
            "irrigation", "drone agriculture", "agricultural tech", "agricultural ai",
            "vertical farm", "indoor farm", "livestock tech", "aquaculture",
        ],
        3,
    ),
    (
        [
            "iot", "edge ai", "edge computing", "edge inference", "tinyml",
            "embedded ai", "sensor network", "connected device", "industrial iot",
            "iiot", "real-time ai", "on-device ai", "fog computing",
        ],
        2,
    ),
    (
        [
            "startup", "funding", "venture capital", "series a", "series b", "series c",
            "seed round", "pre-seed", "angel round", "investment round", "raise",
            "valuation", "unicorn", "accelerator", "incubator", "vc fund",
            "growth equity", "acquisition", "ipo",
        ],
        2,
    ),
]


def _normalize(text: str) -> str:
    """Lowercase and strip non-alphanumeric chars for duplicate detection."""
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _score(article: dict) -> int:
    text = (article["title"] + " " + article["description"]).lower()
    total = 0
    for keywords, points in SCORING_RULES:
        if any(kw in text for kw in keywords):
            total += points
    return total


def filter_and_rank(articles: list[dict], top_n: int = 5) -> list[dict]:
    """
    1. Deduplicate by URL and normalized title.
    2. Score each article.
    3. Sort by (score DESC, date DESC).
    4. Return top_n.
    """
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    unique: list[dict] = []

    for article in articles:
        url = article["link"]
        norm = _normalize(article["title"])

        if url in seen_urls or norm in seen_titles:
            continue

        seen_urls.add(url)
        seen_titles.add(norm)
        unique.append(article)

    logger.info("After dedup: %d articles (from %d)", len(unique), len(articles))

    for article in unique:
        article["score"] = _score(article)

    ranked = sorted(unique, key=lambda a: (a["score"], a["date"]), reverse=True)

    # Prefer articles with at least one keyword match
    qualified = [a for a in ranked if a["score"] > 0]
    if not qualified:
        logger.warning("No articles scored > 0 — using top articles by recency")
        qualified = ranked  # fallback: return most recent

    top = qualified[:top_n]
    for i, a in enumerate(top, 1):
        logger.info(
            "  #%d score=%d  %s",
            i, a["score"],
            a["title"][:80],
        )
    return top
