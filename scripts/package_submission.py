"""Package an explicit allowlist, never a recursive zip of the working directory."""
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/source/TeamBifrost_Submission.zip"
ROOT_FILES = ["README.md", "THIRD_PARTY_NOTICES.md", "pyproject.toml", "requirements.txt", "requirements-report.txt", "setup.bat", "launch.bat", "verify.bat", ".gitignore", "brag.mp4"]
files = [ROOT / name for name in ROOT_FILES]
for path in files:
    if not path.is_file():
        raise FileNotFoundError(f"Required submission file missing: {path.name}")
for directory, patterns in {
    "vaaniverify": ["*.py"], "web": ["*.html", "*.css", "*.js", "*.svg"],
    "tests": ["*.py"], "scripts": ["*.py"], "docs": ["*.md"],
    "examples": ["*.json"], "evidence": ["*.json", "*.csv", "*.xml"],
    "evidence/screenshots": ["*.jpg"], "output/pdf": ["TeamBifrost_Report.pdf"],
}.items():
    for pattern in patterns:
        files.extend((ROOT / directory).glob(pattern))
files = sorted(set(path for path in files if path.is_file() and path.name != "manifest.json"))
secrets_to_exclude = []
for name in ("agent-key.txt", "console-url.txt", "model-key.txt"):
    path = ROOT / ".runtime" / name
    if path.exists():
        value = path.read_text(encoding="utf-8").strip().split("bootstrap=")[-1]
        secrets_to_exclude.append(value.encode())
manifest = []
for path in files:
    data = path.read_bytes()
    if any(secret and secret in data for secret in secrets_to_exclude):
        raise RuntimeError(f"Refusing to package runtime credential in {path.relative_to(ROOT)}")
    manifest.append({"path": path.relative_to(ROOT).as_posix(), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
manifest_path = ROOT / "evidence/manifest.json"
manifest_path.write_text(json.dumps({"files": manifest, "excludes": [".runtime", ".venv", ".pytest_runs", ".local-model", "tmp", "private credentials"]}, indent=2), encoding="utf-8")
OUT.parent.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(OUT, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
    for path in files + [manifest_path]:
        archive.write(path, "VaaniVerify/" + path.relative_to(ROOT).as_posix())
with zipfile.ZipFile(OUT) as archive:
    assert archive.testzip() is None
    assert not any(any(part in name.split("/") for part in (".runtime", ".venv", ".pytest_runs", ".local-model", "tmp")) for name in archive.namelist())
print(f"Packaged {len(files)+1} files: {OUT}")
print(f"Archive SHA-256: {hashlib.sha256(OUT.read_bytes()).hexdigest()}")
