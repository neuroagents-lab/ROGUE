from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict


def build_instruction(task_config: Dict[str, Any]) -> str:
    """Build a materialized instruction string from structured task fields.

    If `instruction_parts` is not present, fall back to the existing
    top-level `instruction` field unchanged.
    """
    parts = task_config.get("instruction_parts")
    if not isinstance(parts, dict):
        return task_config.get("instruction", "")

    flags = task_config.get("instruction_flags", {})
    if not isinstance(flags, dict):
        flags = {}

    chunks = []

    base_instruction = parts.get("base_instruction", "")
    if isinstance(base_instruction, str) and base_instruction.strip():
        chunks.append(base_instruction.strip())

    for key, value in parts.items():
        if key == "base_instruction":
            continue
        if not isinstance(value, str) or not value.strip():
            continue

        include_key = f"include_{key}"
        if flags.get(include_key, True):
            chunks.append(value.strip())

    return "\n\n".join(chunks)


def normalize_task_config(task_config: Dict[str, Any]) -> Dict[str, Any]:
    """Return a task config with `instruction` materialized from structured parts."""
    normalized = deepcopy(task_config)
    normalized["instruction"] = build_instruction(normalized)
    return normalized


def result_model_name(model: str) -> str:
    """Flatten provider-qualified model names into a single path segment."""
    return model.replace("\\", "__").replace("/", "__")
