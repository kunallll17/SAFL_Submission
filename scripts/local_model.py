"""Optional, pinned local inference runtime. No cloud service or paid API."""
import argparse
import hashlib
import json
import secrets
import subprocess
import zipfile
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".local-model"
MODEL_REVISION = "91cad51170dc346986eccefdc2dd33a9da36ead9"
ASSETS = [
    {
        "name": "llama-b12020-bin-win-cpu-x64.zip",
        "url": "https://github.com/ggml-org/llama.cpp/releases/download/b12020/llama-b12020-bin-win-cpu-x64.zip",
        "sha256": "07e81782f5a16c7ffef42403183808e02f271c9ece3aa2d64040b2620ae8d519",
        "bytes": 24574627,
    },
    {
        "name": "qwen2.5-1.5b-instruct-q4_k_m.gguf",
        "url": f"https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/{MODEL_REVISION}/qwen2.5-1.5b-instruct-q4_k_m.gguf",
        "sha256": "6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e",
        "bytes": 1117320736,
    },
]


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def download(asset):
    target = CACHE / asset["name"]
    if target.exists() and sha256(target) == asset["sha256"]:
        print(f"Verified cached {target.name}", flush=True)
        return target
    partial = target.with_suffix(target.suffix + ".part")
    offset = partial.stat().st_size if partial.exists() else 0
    if offset < asset["bytes"]:
        with httpx.Client(timeout=120, follow_redirects=True, trust_env=False) as client:
            with client.stream("GET", asset["url"], headers={"Range": f"bytes={offset}-"} if offset else {}) as response:
                response.raise_for_status()
                if response.status_code == 206:
                    if not response.headers.get("content-range", "").startswith(f"bytes {offset}-"):
                        raise RuntimeError("Download resume range does not match the partial file")
                else:
                    offset = 0
                written = offset
                next_log = written + 100_000_000
                with partial.open("ab" if offset else "wb") as stream:
                    for chunk in response.iter_bytes(1024 * 1024):
                        stream.write(chunk)
                        written += len(chunk)
                        if written >= next_log:
                            print(f"{target.name}: {written / 1e6:.0f}/{asset['bytes'] / 1e6:.0f} MB", flush=True)
                            next_log += 100_000_000
    if partial.stat().st_size != asset["bytes"] or sha256(partial) != asset["sha256"]:
        quarantined = partial.with_name(partial.name + ".bad-" + secrets.token_hex(4))
        partial.rename(quarantined)
        raise RuntimeError(f"Checksum/size mismatch; preserved as {quarantined.name}. Rerun setup to download again.")
    partial.replace(target)
    print(f"Downloaded and SHA-256 verified {target.name}", flush=True)
    return target


def setup():
    CACHE.mkdir(exist_ok=True)
    archive, _model = [download(asset) for asset in ASSETS]
    runtime = CACHE / "llama-b12020"
    runtime.mkdir(exist_ok=True)
    with zipfile.ZipFile(archive) as bundle:
        for item in bundle.infolist():
            if not (runtime / item.filename).resolve().is_relative_to(runtime.resolve()):
                raise RuntimeError("Unsafe archive path")
        bundle.extractall(runtime)
    record = {"model": "Qwen/Qwen2.5-1.5B-Instruct-GGUF", "revision": MODEL_REVISION,
              "quantization": "Q4_K_M", "runtime": "llama.cpp b12020 Windows x64 CPU",
              "assets": ASSETS, "device": "CPU", "threads": 6, "context_tokens": 4096}
    (ROOT / "evidence").mkdir(exist_ok=True)
    (ROOT / "evidence/local_model_runtime.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    print("Local runtime ready. Start with: python scripts/local_model.py serve", flush=True)


def serve():
    executables = list((CACHE / "llama-b12020").rglob("llama-server.exe"))
    model = CACHE / ASSETS[1]["name"]
    if len(executables) != 1 or not model.exists():
        raise SystemExit("Run python scripts/local_model.py setup first.")
    key_file = ROOT / ".runtime/model-key.txt"
    key_file.parent.mkdir(exist_ok=True)
    if not key_file.exists():
        key_file.write_text(secrets.token_urlsafe(32), encoding="utf-8")
    command = [str(executables[0]), "-m", str(model), "--host", "127.0.0.1", "--port", "8770",
               "-c", "4096", "-np", "1", "-t", "6", "-ngl", "0", "--no-webui",
               "--api-key-file", str(key_file), "--alias", "vaaniverify-local"]
    subprocess.run(command, check=True, cwd=ROOT)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["setup", "serve"])
    args = parser.parse_args()
    setup() if args.operation == "setup" else serve()
