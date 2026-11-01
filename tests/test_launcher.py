import socket
import sys

import httpx

from vaaniverify import __main__ as launcher


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def test_launcher_closes_its_gateway_process_tree(tmp_path, monkeypatch):
    console_port, gateway_port = free_port(), free_port()
    while gateway_port == console_port:
        gateway_port = free_port()
    monkeypatch.setattr(sys, "argv", ["vaaniverify", "--no-browser", "--port", str(console_port), "--gateway-port", str(gateway_port)])
    observed = []

    def console_exits_normally(*args, **kwargs):
        observed.append(httpx.get(f"http://127.0.0.1:{gateway_port}/health", trust_env=False).json()["status"])

    monkeypatch.setattr(launcher.uvicorn, "run", console_exits_normally)
    launcher.main(runtime_dir=tmp_path)
    assert observed == ["ok"]
    # Port re-binding directly proves the listener was released, without relying
    # on platform/firewall-specific refused-versus-timeout HTTP errors.
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", gateway_port))
