from __future__ import annotations

import json
from pathlib import Path

import requests


def extract_and_save(file_path: Path, output_dir: Path, api_url: str) -> Path:
    """POST .835 file to FastAPI, save JSON response, return json path."""
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(file_path, "rb") as f:
        response = requests.post(
            api_url,
            files={"file": (file_path.name, f, "application/octet-stream")},
            timeout=120,
        )

    response.raise_for_status()
    parsed = response.json()

    json_path = output_dir / (file_path.stem + ".json")
    json_path.write_text(
        json.dumps(parsed, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return json_path
