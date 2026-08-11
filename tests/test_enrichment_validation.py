from __future__ import annotations

from jrnl.enrichment import parse_enrichment_response, strip_code_fences


def test_strip_code_fences_removes_wrappers() -> None:
    assert strip_code_fences("```json\n{\"x\": 1}\n```") == "{\"x\": 1}"


def test_parse_enrichment_response_falls_back_when_fields_missing() -> None:
    result = parse_enrichment_response("{\"tags\": [1, \"Work\"]}", "one two three four five six seven eight nine ten eleven")

    assert result.summary == "one two three four five six seven eight nine ten"
    assert result.mood == "neutral"
    assert result.tags == ["work"]
