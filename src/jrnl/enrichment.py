from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Sequence

import httpx

from jrnl.prompts import ENRICHMENT_PROMPT

MOODS = ("happy", "sad", "anxious", "angry", "calm", "excited", "neutral", "mixed")


@dataclass(slots=True)
class EnrichmentResult:
    summary: str | None
    mood: str | None
    tags: list[str]


def strip_code_fences(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped

    lines = stripped.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


def fallback_summary(entry_text: str) -> str:
    return " ".join(entry_text.split()[:10])


def normalize_tags(tags: object) -> list[str]:
    if not isinstance(tags, list):
        return []

    normalized: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        if not isinstance(tag, str):
            continue
        cleaned = tag.strip().lower()
        if not cleaned or cleaned in seen:
            continue
        normalized.append(cleaned)
        seen.add(cleaned)
        if len(normalized) == 5:
            break
    return normalized


def parse_enrichment_response(raw_text: str, entry_text: str) -> EnrichmentResult:
    data = json.loads(strip_code_fences(raw_text))

    summary = data.get("summary")
    if isinstance(summary, str) and summary.strip():
        summary_value: str | None = summary.strip()
    else:
        summary_value = fallback_summary(entry_text)

    mood = data.get("mood")
    mood_value = mood if isinstance(mood, str) and mood in MOODS else "neutral"
    tags = normalize_tags(data.get("tags"))
    return EnrichmentResult(summary=summary_value, mood=mood_value, tags=tags)


def build_enrichment_prompt(entry_text: str, existing_tags: Sequence[str]) -> str:
    return ENRICHMENT_PROMPT.format(
        existing_tags_comma_separated=", ".join(existing_tags) or "(none)",
        entry_text=entry_text,
    )


def enrich_entry(
    client: object,
    *,
    model: str,
    entry_text: str,
    existing_tags: Sequence[str],
) -> EnrichmentResult:
    prompt = build_enrichment_prompt(entry_text, existing_tags)
    try:
        raw_text = client.generate(model, prompt, format="json")
    except (httpx.HTTPError, TimeoutError, OSError):
        return EnrichmentResult(summary=None, mood=None, tags=[])

    return parse_enrichment_response(raw_text, entry_text)
