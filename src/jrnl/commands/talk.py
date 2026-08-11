from __future__ import annotations

import json
import random

import click

from jrnl.config import ensure_config
from jrnl.db import connect, get_recent_entries, initialize_database, list_tags, save_entry, save_transcript
from jrnl.enrichment import enrich_entry
from jrnl.ollama_client import OllamaClient
from jrnl.prompts import CHAT_COMPILE_PROMPT, CHAT_OPENING_PROMPTS, CHAT_SYSTEM_PROMPT


def _format_transcript_for_prompt(transcript: list[dict[str, str]]) -> str:
    lines: list[str] = []
    for turn in transcript:
        speaker = "Assistant" if turn["role"] == "ai" else "User"
        lines.append(f"{speaker}: {turn['text']}")
    return "\n".join(lines)


def _compile_entry_text(client: OllamaClient, model: str, transcript: list[dict[str, str]]) -> str:
    prompt = CHAT_COMPILE_PROMPT.format(transcript=_format_transcript_for_prompt(transcript))
    try:
        compiled = client.generate(model, prompt)
    except Exception:
        compiled = ""

    compiled = compiled.strip()
    if compiled:
        return compiled

    user_lines = [turn["text"] for turn in transcript if turn["role"] == "user" and turn["text"].strip()]
    if user_lines:
        return " ".join(user_lines).strip()
    return "Nothing much happened."


def _chat_messages(transcript: list[dict[str, str]], recent_context: str) -> list[dict[str, str]]:
    messages = [{"role": "system", "content": CHAT_SYSTEM_PROMPT.format(recent_context=recent_context)}]
    for turn in transcript:
        role = "assistant" if turn["role"] == "ai" else "user"
        messages.append({"role": role, "content": turn["text"]})
    return messages


def _recent_context_text(recent_entries: list[dict[str, str]]) -> str:
    if not recent_entries:
        return "none"

    parts: list[str] = []
    for entry in recent_entries:
        summary = entry["summary"] or entry["raw_text"]
        parts.append(f"{entry['created_at']}: {summary}")
    return " | ".join(parts)


@click.command()
def talk() -> None:
    config = ensure_config()
    initialize_database(config.storage.db_path)

    client = OllamaClient(config.ollama.host, config.ollama.timeout_seconds)
    transcript: list[dict[str, str]] = []
    with connect(config.storage.db_path) as connection:
        recent_entries = get_recent_entries(connection)

    opening = random.choice(CHAT_OPENING_PROMPTS)
    if recent_entries and random.random() < 0.33:
        opening = f"Following up — {recent_entries[0]['summary'] or recent_entries[0]['raw_text']} — how's that going?"
    transcript.append({"role": "ai", "text": opening})
    click.echo(f"AI: {opening}")

    while True:
        user_text = click.prompt("You", default="", show_default=False)
        user_text = user_text.strip()
        if not user_text:
            continue
        if user_text == "/done":
            break

        transcript.append({"role": "user", "text": user_text})
        assistant_text = ""
        try:
            assistant_text = client.chat(
                config.ollama.model,
                _chat_messages(transcript, _recent_context_text(recent_entries)),
            ).strip()
        except Exception:
            assistant_text = "Tell me a bit more if you want."

        if not assistant_text:
            assistant_text = "Tell me a bit more if you want."

        transcript.append({"role": "ai", "text": assistant_text})
        click.echo(f"AI: {assistant_text}")

    compiled_text = _compile_entry_text(client, config.ollama.model, transcript)

    with connect(config.storage.db_path) as connection:
        existing_tags = list_tags(connection)
        enrichment = enrich_entry(
            client,
            model=config.ollama.model,
            entry_text=compiled_text,
            existing_tags=existing_tags,
        )
        entry_id = save_entry(
            connection,
            source="talk",
            raw_text=compiled_text,
            summary=enrichment.summary,
            mood=enrichment.mood,
            tags=enrichment.tags,
        )
        save_transcript(connection, entry_id=entry_id, raw_json=json.dumps(transcript, ensure_ascii=False))

    click.echo(f"Saved entry #{entry_id}.")
