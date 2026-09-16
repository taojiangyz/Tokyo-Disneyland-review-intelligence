from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PromptTemplate:
    prompt_id: str
    version: str
    text: str

    def render(self, **values: Any) -> str:
        placeholders = set(
            re.findall(r"\{\{([A-Za-z_][A-Za-z0-9_]*)\}\}", self.text)
        )
        missing = placeholders - set(values)
        if missing:
            names = ", ".join(sorted(missing))
            raise ValueError(
                f"Missing placeholder value(s) for prompt {self.prompt_id}: {names}"
            )
        rendered = self.text
        for key in placeholders:
            value = values[key]
            rendered = rendered.replace(f"{{{{{key}}}}}", str(value))
        return rendered


class PromptRegistry:
    """Load versioned prompts from files instead of embedding them in code."""

    def __init__(self, prompt_dir: Path | None = None) -> None:
        configured = os.getenv("ALADDIN_PROMPT_DIR")
        self.prompt_dir = prompt_dir or (
            Path(configured) if configured else Path(__file__).parents[1] / "prompts"
        )
        metadata_path = self.prompt_dir / "registry.json"
        self._metadata: dict[str, dict[str, str]] = json.loads(
            metadata_path.read_text(encoding="utf-8")
        )

    def get(self, prompt_id: str) -> PromptTemplate:
        try:
            entry = self._metadata[prompt_id]
        except KeyError as exc:
            raise KeyError(f"Unknown prompt id: {prompt_id}") from exc
        text = (self.prompt_dir / entry["file"]).read_text(encoding="utf-8")
        return PromptTemplate(
            prompt_id=prompt_id,
            version=entry["version"],
            text=text,
        )
