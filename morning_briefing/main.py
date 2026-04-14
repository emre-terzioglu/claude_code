#!/usr/bin/env python3
"""
Morning Briefing — Daily AI-powered podcast + email.

Orchestration flow:
  1. Fetch Google News RSS (3 topic areas, last 24 h)
  2. Deduplicate, score, and rank articles
  3. Gemini: strategic analysis
  4. Gemini: podcast script (2-3 min)
  5. Google TTS: script -> MP3
  6. Gmail SMTP: send email with MP3 attachment

Run manually:   python main.py
Cron schedule:  15 7 * * 1-5  (07:15 Europe/Berlin on weekdays)
"""

import logging
import os
import sys
import tempfile
from datetime import datetime

import pytz
from dotenv import load_dotenv

# Load .env before any module that reads env vars
load_dotenv()

from email_sender import send_briefing_email
from gemini_analyzer import analyze_articles, generate_podcast_script
from news_fetcher import fetch_all_articles
from scorer import filter_and_rank
from tts_generator import generate_audio

# ---------------------------------------------------------------------------
# Logging — file + stdout so cron captures everything
# ---------------------------------------------------------------------------
LOG_FILE = os.path.join(os.path.dirname(__file__), "morning_briefing.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
RECIPIENT = "emre.terzioglu@icloud.com"
BERLIN_TZ = pytz.timezone("Europe/Berlin")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_email_body(articles: list[dict], analysis: str, script: str) -> str:
    lines = [
        "MORNING BRIEFING",
        "=" * 60,
        "",
        "TOP ARTICLES",
        "-" * 60,
    ]
    for i, a in enumerate(articles, 1):
        lines += [
            f"{i}. {a['title']}",
            f"   Score: {a['score']}  |  {a['date'].strftime('%Y-%m-%d %H:%M UTC')}",
            f"   {a['link']}",
            "",
        ]
    lines += [
        "STRATEGIC ANALYSIS",
        "-" * 60,
        analysis,
        "",
        "PODCAST SCRIPT",
        "-" * 60,
        script,
    ]
    return "\n".join(lines)


def _send_error_notification(date_str: str, error: str) -> None:
    """Best-effort error email — never raises."""
    try:
        send_briefing_email(
            recipient=RECIPIENT,
            subject=f"Morning Briefing {date_str} — ERROR",
            body=f"The morning briefing pipeline failed.\n\nError:\n{error}",
            mp3_path=None,
            date_str=date_str,
        )
        logger.info("Error notification sent")
    except Exception as exc:
        logger.error("Could not send error notification: %s", exc)


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run() -> None:
    now = datetime.now(BERLIN_TZ)
    date_str = now.strftime("%Y-%m-%d")
    logger.info("=" * 60)
    logger.info("Morning Briefing starting — %s", now.strftime("%Y-%m-%d %H:%M %Z"))

    # ------------------------------------------------------------------
    # Step 1: Fetch news
    # ------------------------------------------------------------------
    logger.info("Step 1: Fetching news…")
    try:
        raw_articles = fetch_all_articles()
    except Exception as exc:
        msg = f"News fetch failed: {exc}"
        logger.error(msg)
        _send_error_notification(date_str, msg)
        sys.exit(1)

    if not raw_articles:
        msg = "No articles found in the last 24 hours."
        logger.warning(msg)
        _send_error_notification(date_str, msg)
        sys.exit(0)

    # ------------------------------------------------------------------
    # Step 2: Filter and rank
    # ------------------------------------------------------------------
    logger.info("Step 2: Filtering and ranking…")
    top_articles = filter_and_rank(raw_articles)

    if not top_articles:
        msg = "No articles passed quality filtering."
        logger.warning(msg)
        _send_error_notification(date_str, msg)
        sys.exit(0)

    logger.info("Selected %d articles for analysis", len(top_articles))

    # ------------------------------------------------------------------
    # Step 3: Strategic analysis (Gemini call 1)
    # ------------------------------------------------------------------
    logger.info("Step 3: Generating strategic analysis…")
    try:
        analysis = analyze_articles(top_articles)
    except Exception as exc:
        msg = f"Gemini analysis failed: {exc}"
        logger.error(msg)
        _send_error_notification(date_str, msg)
        sys.exit(1)

    # ------------------------------------------------------------------
    # Step 4: Podcast script (Gemini call 2)
    # ------------------------------------------------------------------
    logger.info("Step 4: Generating podcast script…")
    try:
        script = generate_podcast_script(analysis)
        logger.info("Script: %d chars", len(script))
    except Exception as exc:
        msg = f"Script generation failed: {exc}"
        logger.error(msg)
        _send_error_notification(date_str, msg)
        sys.exit(1)

    # ------------------------------------------------------------------
    # Step 5: Text-to-Speech -> MP3
    # ------------------------------------------------------------------
    logger.info("Step 5: Converting script to audio…")
    mp3_path = os.path.join(tempfile.gettempdir(), f"morning_briefing_{date_str}.mp3")
    tts_ok = False
    try:
        generate_audio(script, mp3_path)
        tts_ok = True
    except Exception as exc:
        logger.error("TTS failed: %s — will send text-only email", exc)

    # ------------------------------------------------------------------
    # Step 6: Send email
    # ------------------------------------------------------------------
    logger.info("Step 6: Sending email…")
    email_body = _build_email_body(top_articles, analysis, script)
    subject = f"Morning Briefing — {date_str}"
    if not tts_ok:
        subject += " (text only — audio unavailable)"

    try:
        send_briefing_email(
            recipient=RECIPIENT,
            subject=subject,
            body=email_body,
            mp3_path=mp3_path if tts_ok else None,
            date_str=date_str,
        )
    except Exception as exc:
        logger.error("Email delivery failed: %s", exc)
        sys.exit(1)

    # ------------------------------------------------------------------
    # Cleanup temp file
    # ------------------------------------------------------------------
    if tts_ok:
        try:
            os.remove(mp3_path)
        except OSError:
            pass

    logger.info("Morning Briefing completed successfully.")
    logger.info("=" * 60)


if __name__ == "__main__":
    run()
