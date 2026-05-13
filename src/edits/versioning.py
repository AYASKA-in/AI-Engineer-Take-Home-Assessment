from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from src.utils import dump_json, load_json


TEMPLATE_HISTORY_PATH = "data/template_history.jsonl"


def record_template_version(
    template_path: str | Path,
    record_id: str,
    patterns: list[str],
    history_path: str | Path = TEMPLATE_HISTORY_PATH,
) -> dict:
    template_data = load_json(template_path, {})
    version_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "record_id": record_id,
        "triggered_patterns": patterns,
        "settings_snapshot": template_data,
    }
    history_file = Path(history_path)
    history_file.parent.mkdir(parents=True, exist_ok=True)
    with history_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(version_entry) + "\n")
    return version_entry


def load_template_history(history_path: str | Path = TEMPLATE_HISTORY_PATH) -> list[dict]:
    history_file = Path(history_path)
    if not history_file.exists():
        return []
    entries = []
    for line in history_file.read_text(encoding="utf-8").splitlines():
        if line.strip():
            entries.append(json.loads(line))
    return entries


def get_latest_version(history_path: str | Path = TEMPLATE_HISTORY_PATH) -> dict | None:
    history = load_template_history(history_path)
    return history[-1] if history else None
