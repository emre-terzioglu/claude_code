"""
Google Gemini API integration.

Two calls:
  1. analyze_articles()  -> strategic analysis per article
  2. generate_podcast_script()  -> 2-3 min spoken script
"""

import logging
import os
import time

import google.generativeai as genai

logger = logging.getLogger(__name__)

_MODEL_NAME = "gemini-1.5-pro"
_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 4  # seconds; doubles each attempt


def _model() -> genai.GenerativeModel:
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise EnvironmentError("GEMINI_API_KEY is not set")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(_MODEL_NAME)


def _call(model: genai.GenerativeModel, prompt: str) -> str:
    """Call Gemini with exponential-backoff retries."""
    last_exc: Exception | None = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception as exc:
            last_exc = exc
            wait = _RETRY_BASE_DELAY * (2 ** (attempt - 1))
            logger.warning(
                "Gemini call attempt %d/%d failed (%s). Retrying in %ds…",
                attempt, _MAX_RETRIES, exc, wait,
            )
            if attempt < _MAX_RETRIES:
                time.sleep(wait)

    raise RuntimeError(f"Gemini API failed after {_MAX_RETRIES} attempts: {last_exc}") from last_exc


def analyze_articles(articles: list[dict]) -> str:
    """
    First Gemini call: strategic analysis per article.
    Applies the critical thinking filter — only business-viable insights survive.
    """
    model = _model()

    articles_block = "\n\n".join(
        f"[{i}] {a['title']}\n"
        f"    Date: {a['date'].strftime('%Y-%m-%d %H:%M UTC')}\n"
        f"    Summary: {a['description'][:450]}"
        for i, a in enumerate(articles, 1)
    )

    prompt = f"""You are a strategic analyst advising a startup founder active in AgTech, IoT, and venture capital.

CRITICAL FILTER: Only include an insight if you can articulate a realistic business opportunity.
If an article has no actionable angle, dismiss it in one sentence — do not pad.

For each relevant article below, answer these five questions:
1. **What happened** — one crisp, factual sentence.
2. **Why it matters** — concrete market or business impact (numbers if possible).
3. **Hidden opportunity** — a non-obvious angle a smart founder could exploit TODAY.
4. **Potential threat** — who loses or what risks emerge in the next 12 months.
5. **Actionable idea** — one highly specific, implementable move (not generic advice).

---
{articles_block}
---

Be direct. No filler. No bullet-point repetition of the headline. Analysts get fired for summaries."""

    logger.info("Gemini call 1: strategic analysis…")
    return _call(model, prompt)


def generate_podcast_script(analysis: str) -> str:
    """
    Second Gemini call: turn the analysis into a 2-3 minute spoken podcast script.
    """
    model = _model()

    prompt = f"""You are writing a morning briefing podcast for a startup founder in AgTech, IoT, and venture capital.

Transform the analysis below into a 2–3 minute spoken script (~300–420 words at 130 wpm).

TONE:
- Direct, confident, no fluff — every sentence earns its place.
- Insight-dense but conversational. Think: smart friend on a call, not a news anchor.

STRUCTURE:
1. Hook opener (10–15 sec): Start with the most striking insight or tension — NOT "Good morning" or "Welcome to".
2. Three to five key insights (90–120 sec): Deliver each in 2–3 punchy sentences. Prioritize what the listener can act on.
3. Focus for today (20–30 sec): End with ONE clear, specific watch item or move for today. Make it stick.

STRICT RULES:
- Write ONLY the spoken words. Zero stage directions, zero [brackets], zero headers.
- No filler phrases: "It's important to note that…", "In today's rapidly changing landscape…"
- If an insight has no business relevance, skip it entirely.

---
ANALYSIS:
{analysis}
---"""

    logger.info("Gemini call 2: podcast script…")
    return _call(model, prompt)
