"""Start both local services and open the private owner console."""
import argparse
import json
import secrets
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

import httpx
import uvicorn

from .capabilities import b64
from .gateway import Gateway
from .kernel import Kernel
from .server import create_app


def main(runtime_dir: Path | None = None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--gateway-port", type=int, default=8766)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    if args.port == args.gateway_port:
        parser.error("Console and gateway need different ports")
    for port in (args.port, args.gateway_port):
        with socket.socket() as probe:
            try:
                probe.bind(("127.0.0.1", port))
            except OSError:
                parser.error(f"Port {port} is already in use. Stop the old demo or choose another port.")
    root = Path(__file__).resolve().parents[1]
    runtime = runtime_dir or root / ".runtime"
    runtime.mkdir(exist_ok=True)
    kernel = Kernel()
    bootstrap, agent_key = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    public = b64(kernel.signing_key.public_key().public_bytes_raw())
    database = runtime / "ledger.sqlite3"
    gateway = Gateway(kernel.signing_key.public_key(), database)
    origin = f"http://127.0.0.1:{args.port}"
    gateway_url = f"http://127.0.0.1:{args.gateway_port}"
    private_url = f"{origin}/#bootstrap={bootstrap}"
    (runtime / "console-url.txt").write_text(private_url, encoding="utf-8")
    (runtime / "agent-key.txt").write_text(agent_key, encoding="utf-8")
    (runtime / "public-key.txt").write_text(public, encoding="utf-8")
    (runtime / "process.json").write_text(json.dumps({"console_port": args.port, "gateway_port": args.gateway_port}), encoding="utf-8")
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    with (runtime / "gateway.log").open("a", encoding="utf-8") as logfile:
        process = subprocess.Popen([sys.executable, "-m", "vaaniverify.gateway_runner", "--public-key", public,
                                    "--database", str(database), "--port", str(args.gateway_port)], cwd=root,
                                   stdout=logfile, stderr=subprocess.STDOUT, creationflags=flags)
        try:
            for _ in range(50):
                if process.poll() is not None:
                    raise RuntimeError("Gateway failed to start; see .runtime/gateway.log")
                try:
                    if httpx.get(gateway_url + "/health", timeout=.4, trust_env=False).status_code == 200:
                        break
                except httpx.HTTPError:
                    time.sleep(.1)
            else:
                raise RuntimeError("Gateway startup timed out")
            print(f"VaaniVerify console: {origin}")
            print("Private launch link: .runtime/console-url.txt (do not share)")
            print("Synthetic data only. Press Ctrl+C to stop both services.")
            if not args.no_browser:
                # Opening before run is safe: a short timer lets the server bind first.
                import threading
                threading.Timer(1.2, lambda: webbrowser.open(private_url)).start()
            uvicorn.run(create_app(kernel, gateway, bootstrap, agent_key, origin, gateway_url),
                        host="127.0.0.1", port=args.port, log_level="warning", access_log=False)
        finally:
            if sys.platform == "win32" and process.poll() is None:
                # Windows venv python.exe is a launcher with an interpreter child.
                # Terminating only the launcher would leave the gateway listening.
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            elif process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == "__main__":
    main()
