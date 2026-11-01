"""Capture installed dependency versions and licences without personal paths."""
import importlib.metadata
import json
from pathlib import Path

rows = []
for distribution in importlib.metadata.distributions():
    meta = distribution.metadata
    rows.append({"name": meta["Name"], "version": distribution.version,
                 "license": meta.get("License-Expression") or meta.get("License") or "See upstream licence files",
                 "homepage": meta.get("Home-page") or ""})
path = Path(__file__).resolve().parents[1] / "evidence/dependencies.json"
path.parent.mkdir(exist_ok=True)
path.write_text(json.dumps(sorted(rows, key=lambda r: r["name"].lower()), indent=2), encoding="utf-8")
print(f"Recorded {len(rows)} installed packages in {path}")
