"""Minimal proposal-only adapter. Connect any model upstream of this boundary."""

import argparse
import json
from pathlib import Path

import httpx

from .models import ProposalInput


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--intent-id", required=True, help="ID created by the trusted owner console")
    parser.add_argument("--proposal", type=Path, required=True, help="JSON with action, agent_message and external_text")
    parser.add_argument("--key-file", type=Path, default=Path(".runtime/agent-key.txt"))
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    raw = json.loads(args.proposal.read_text(encoding="utf-8"))
    proposal = ProposalInput(intent_id=args.intent_id, **raw)
    credential = args.key_file.read_text(encoding="utf-8").strip()
    response = httpx.post(f"http://127.0.0.1:{args.port}/api/agent/proposals",
                          json=proposal.model_dump(mode="json"), headers={"Authorization": "Bearer " + credential},
                          timeout=10, trust_env=False)
    # ASCII JSON also works under legacy Windows console encodings. JSON readers
    # recover the original multilingual text from the escaped code points.
    print(json.dumps(response.json(), ensure_ascii=True, indent=2))
    response.raise_for_status()


if __name__ == "__main__":
    main()
