#!/usr/bin/env python3
"""Concurrent client check; requires a server running on the selected port."""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import subprocess
import sys


def submit(index: int, host: str, port: int) -> dict:
    result = subprocess.run(
        [
            sys.executable, "client.py",
            json.dumps({"task": "demo", "client": index}),
            "--host", host, "--port", str(port),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return json.loads(result.stdout)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--count", type=int, default=8)
    args = parser.parse_args()
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.count) as pool:
        acknowledgements = list(pool.map(lambda i: submit(i, args.host, args.port), range(args.count)))
    ids = [item.get("job_id") for item in acknowledgements]
    assert all(item.get("status") == "queued" for item in acknowledgements), acknowledgements
    assert len(set(ids)) == args.count, f"job IDs are not unique: {ids}"
    print(f"PASS: {args.count} concurrent clients received queued acknowledgements and unique IDs")
    print("Job IDs: " + ", ".join(sorted(ids)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
