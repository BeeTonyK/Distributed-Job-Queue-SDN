#!/usr/bin/env python3
"""Submit one JSON job to the TCP job queue and print its acknowledgement."""
from __future__ import annotations

import argparse
import json
import socket
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("payload", help="job text, or a JSON value prefixed with @")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args()

    payload = args.payload
    if payload.startswith("@"):
        try:
            payload = json.loads(payload[1:])
        except json.JSONDecodeError as exc:
            parser.error(f"invalid JSON payload after @: {exc}")

    request = {"type": "submit", "payload": payload}
    try:
        with socket.create_connection((args.host, args.port), timeout=args.timeout) as sock:
            sock.sendall((json.dumps(request) + "\n").encode("utf-8"))
            with sock.makefile("r", encoding="utf-8") as stream:
                line = stream.readline()
        if not line:
            raise ConnectionError("server closed connection without replying")
        response = json.loads(line)
        print(json.dumps(response, indent=2))
        return 0 if response.get("status") == "queued" else 1
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Submission failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
