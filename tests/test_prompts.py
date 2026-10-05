from pathlib import Path

import pytest

from app.prompts import PromptRegistry, PromptTemplate


def test_registry_loads_versioned_agent_prompt() -> None:
    registry = PromptRegistry()
    prompt = registry.get("agent_answer")

    assert prompt.version == "2.0.0"
    assert "{{analytics_json}}" in prompt.text


def test_prompt_render_replaces_all_values() -> None:
    prompt = PromptTemplate("test", "1.0.0", "Question: {{query}}")
    assert prompt.render(query="Why?") == "Question: Why?"


def test_prompt_render_rejects_unresolved_placeholder() -> None:
    prompt = PromptTemplate("test", "1.0.0", "{{query}} {{missing}}")
    with pytest.raises(ValueError, match="Missing placeholder value"):
        prompt.render(query="Why?")


def test_prompt_render_allows_braces_inside_user_content() -> None:
    prompt = PromptTemplate("test", "1.0.0", "Question: {{query}}")
    assert prompt.render(query="Explain {{customer_data}}") == (
        "Question: Explain {{customer_data}}"
    )


def test_registry_can_be_loaded_from_explicit_directory(tmp_path: Path) -> None:
    (tmp_path / "registry.json").write_text(
        '{"sample":{"version":"2.0.0","file":"sample.txt"}}',
        encoding="utf-8",
    )
    (tmp_path / "sample.txt").write_text("Hello {{name}}", encoding="utf-8")
    prompt = PromptRegistry(tmp_path).get("sample")
    assert prompt.version == "2.0.0"
    assert prompt.render(name="Aladdin") == "Hello Aladdin"
