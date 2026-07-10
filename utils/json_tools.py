from __future__ import annotations

import json
import re
from typing import Any


def extract_json(text: str) -> Any:
    """Parse raw JSON, or the first JSON object/array inside markdown text."""
    stripped = text.strip()
    if not stripped:
        raise ValueError("Empty JSON response")

    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    fenced = re.search(r"```(?:json)?\s*(.*?)```", stripped, re.DOTALL)
    if fenced:
        return json.loads(fenced.group(1).strip())

    first_array = stripped.find("[")
    first_object = stripped.find("{")
    starts = [idx for idx in [first_array, first_object] if idx != -1]
    if not starts:
        raise ValueError("No JSON object or array found")

    start = min(starts)
    opener = stripped[start]
    closer = "]" if opener == "[" else "}"
    end = stripped.rfind(closer)
    if end == -1 or end <= start:
        raise ValueError("Incomplete JSON response")

    return json.loads(stripped[start : end + 1])

