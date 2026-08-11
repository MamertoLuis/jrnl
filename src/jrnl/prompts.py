from __future__ import annotations

ENRICHMENT_PROMPT = (
    "You are analyzing a personal journal entry. Respond with ONLY a JSON object, no other text.\n\n"
    "Existing tags in use: {existing_tags_comma_separated}\n\n"
    "Journal entry:\n\"\"\"\n{entry_text}\n\"\"\"\n\n"
    "Return JSON in this exact format:\n"
    "{{\n"
    '  "summary": "<one sentence, under 15 words, capturing the essence of the entry>",\n'
    '  "mood": "<one of: happy, sad, anxious, angry, calm, excited, neutral, mixed>",\n'
    '  "tags": ["<2 to 5 short lowercase tags>"]\n'
    "}}\n"
)

CHAT_SYSTEM_PROMPT = (
    "You are a gentle journaling companion. The user is having a low-effort or distracted day and wants to talk instead of write.\n"
    "Ask only one question at a time and keep responses short.\n"
    "Recent context: {recent_context}"
)

CHAT_OPENING_PROMPTS = [
    "Hey. Anything on your mind today?",
    "How'd today feel, even if nothing much happened?",
    "What's one thing that stuck with you today?",
]

CHAT_COMPILE_PROMPT = (
    "Turn the user's responses into a short first-person journal entry.\n\n"
    "Conversation:\n{transcript}\n"
)
