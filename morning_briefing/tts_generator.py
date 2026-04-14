"""
Google Cloud Text-to-Speech integration.

Converts the podcast script to MP3. Handles chunking automatically
if the script exceeds Google's 5,000-byte-per-request limit.

Authentication: set GOOGLE_APPLICATION_CREDENTIALS to point at a
service-account JSON key with the Cloud Text-to-Speech API enabled.
"""

import logging
import os

from google.cloud import texttospeech

logger = logging.getLogger(__name__)

_MAX_BYTES = 4_800  # Keep under Google's 5,000-byte hard limit

# Voice: Neural2-D is a natural-sounding US-English male voice.
# Alternatives: en-US-Neural2-F (female), en-US-Studio-O (Studio tier, higher quality).
_VOICE = texttospeech.VoiceSelectionParams(
    language_code="en-US",
    name="en-US-Neural2-D",
    ssml_gender=texttospeech.SsmlVoiceGender.MALE,
)

_AUDIO_CONFIG = texttospeech.AudioConfig(
    audio_encoding=texttospeech.AudioEncoding.MP3,
    speaking_rate=1.05,       # Slight morning energy boost
    pitch=0.0,
    effects_profile_id=["headphone-class-device"],
)


def _split_into_chunks(text: str) -> list[str]:
    """
    Split text at sentence boundaries to stay under _MAX_BYTES per chunk.
    Falls back to hard character splits if a single sentence is too long.
    """
    # Split on sentence-ending punctuation followed by whitespace
    import re
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())

    chunks: list[str] = []
    current = ""

    for sentence in sentences:
        candidate = (current + " " + sentence).strip() if current else sentence
        if len(candidate.encode("utf-8")) <= _MAX_BYTES:
            current = candidate
        else:
            if current:
                chunks.append(current)
            # If a single sentence still exceeds the limit, hard-split it
            if len(sentence.encode("utf-8")) > _MAX_BYTES:
                while sentence:
                    chunk = sentence[:_MAX_BYTES // 3]  # safe char estimate
                    chunks.append(chunk)
                    sentence = sentence[len(chunk):]
                current = ""
            else:
                current = sentence

    if current:
        chunks.append(current)

    return chunks


def generate_audio(script: str, output_path: str) -> str:
    """
    Synthesize `script` to MP3 at `output_path`.
    Returns output_path on success.
    """
    client = texttospeech.TextToSpeechClient()

    byte_size = len(script.encode("utf-8"))
    if byte_size <= _MAX_BYTES:
        chunks = [script]
        logger.info("Script fits in one TTS request (%d bytes)", byte_size)
    else:
        chunks = _split_into_chunks(script)
        logger.info("Script chunked into %d TTS requests (%d bytes total)", len(chunks), byte_size)

    audio_parts: list[bytes] = []
    for idx, chunk in enumerate(chunks, 1):
        logger.debug("TTS request %d/%d (%d bytes)", idx, len(chunks), len(chunk.encode("utf-8")))
        response = client.synthesize_speech(
            input=texttospeech.SynthesisInput(text=chunk),
            voice=_VOICE,
            audio_config=_AUDIO_CONFIG,
        )
        audio_parts.append(response.audio_content)

    with open(output_path, "wb") as fh:
        for part in audio_parts:
            fh.write(part)

    size_kb = os.path.getsize(output_path) / 1024
    logger.info("MP3 written: %s (%.1f KB)", output_path, size_kb)
    return output_path
