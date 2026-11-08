#!/usr/bin/env python3
"""Build a source + prebuilt-assets ZIP, without local state or credentials."""
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
version = (ROOT / "VERSION").read_text().strip()
out = ROOT / "dist" / ("abm-radar-plus-github-ready-v" + version + ".zip")
out.parent.mkdir(exist_ok=True)
excluded = {"node_modules", ".git", "dist", "__pycache__", ".pytest_cache"}
with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
    for path in sorted(ROOT.rglob("*")):
        relative = path.relative_to(ROOT)
        if not path.is_file() or any(part in excluded for part in relative.parts):
            continue
        if path.suffix in {".pyc", ".env", ".db", ".sqlite3", ".log"}:
            continue
        if path.name in {".DS_Store", "config.json", "collector.json"}:
            continue
        archive.write(path, Path("abm-radar-plus") / relative)
print(out)
