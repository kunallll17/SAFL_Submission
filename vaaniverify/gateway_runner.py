"""Standalone verifier process: receives only a public key and ledger location."""
import argparse

import uvicorn
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .capabilities import unb64
from .gateway import Gateway, create_gateway_app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--public-key", required=True)
    parser.add_argument("--database", required=True)
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args()
    gateway = Gateway(Ed25519PublicKey.from_public_bytes(unb64(args.public_key)), args.database)
    uvicorn.run(create_gateway_app(gateway), host="127.0.0.1", port=args.port, log_level="warning", access_log=False)


if __name__ == "__main__":
    main()
