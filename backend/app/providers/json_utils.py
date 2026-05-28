"""Best-effort JSON extraction/repair for LLM outputs.

Models often wrap JSON in ```json fences or add prose around it. Analysis tasks
(mention extraction / claim splitting / recommendations) need reliable JSON, so we
strip fences and slice the outermost {...} or [...] before parsing.
"""
import json
import re

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)


def repair_json(text: str) -> dict | list:
    """Parse JSON from a possibly noisy LLM string. Raises ValueError if unrecoverable."""
    if text is None:
        raise ValueError("empty text")
    candidate = text.strip()

    # 1) direct parse
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    # 2) inside a code fence
    m = _FENCE_RE.search(candidate)
    if m:
        inner = m.group(1).strip()
        try:
            return json.loads(inner)
        except json.JSONDecodeError:
            candidate = inner

    # 3) slice the outermost object/array
    sliced = _slice_outermost(candidate)
    if sliced is not None:
        return json.loads(sliced)

    raise ValueError("no parseable JSON found")


def _slice_outermost(text: str) -> str | None:
    starts = [i for i in (text.find("{"), text.find("[")) if i != -1]
    if not starts:
        return None
    start = min(starts)
    open_ch = text[start]
    close_ch = "}" if open_ch == "{" else "]"
    depth = 0
    in_str = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None
