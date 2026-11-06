"""Parse JSON that PAC CLI may surround with log lines."""

from __future__ import annotations

import json
from typing import Any


def parse_pac_json(text: str) -> Any:
    decoder = json.JSONDecoder()
    found: list[Any] = []
    for index, char in enumerate(text):
        if char not in "[{":
            continue
        try:
            value, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, (list, dict)):
            found.append(value)
    if not found:
        raise ValueError("PAC did not return JSON. Confirm this CLI supports --json.")
    lists = [value for value in found if isinstance(value, list)]
    return lists[-1] if lists else found[-1]


def walk_solution(payload: Any, unique_name: str) -> dict | None:
    if isinstance(payload, dict):
        values = {str(key).lower(): value for key, value in payload.items()}
        for key in ("solutionuniquename", "uniquename", "name"):
            if str(values.get(key, "")).lower() == unique_name.lower():
                return payload
        for value in payload.values():
            found = walk_solution(value, unique_name)
            if found is not None:
                return found
        return None
    if isinstance(payload, list):
        for item in payload:
            found = walk_solution(item, unique_name)
            if found is not None:
                return found
    return None


def field(record: dict, *names: str) -> str:
    folded = {str(key).lower(): value for key, value in record.items()}
    for name in names:
        if name.lower() in folded and folded[name.lower()] is not None:
            return str(folded[name.lower()])
    return ""


def is_managed(record: dict) -> bool:
    raw = field(record, "IsManaged", "ismanaged", "Managed")
    return raw.strip().lower() in {"1", "true", "yes"}
