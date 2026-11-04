#!/usr/bin/env python3
"""Concurrent acceptance check; requires server.py running on localhost:5000."""
from __future__ import annotations

import concurrent.futures
import json
import subprocess
import sys


def submit(index: int) -> dict:
    result = subprocess.run(
        [sys.executable, "client.py", json.dumps({"task": "demo", "client": index})],
        check=True, capture_output=True, text=True,
    )
    return json.loads(result.stdout)


def main() -> int:
    count = 8
    with concurrent.futures.ThreadPoolExecutor(max_workers=count) as pool:
        acknowledgements = list(pool.map(submit, range(count)))
    ids = [item.get("job_id") for item in acknowledgements]
    assert all(item.get("status") == "queued" for item in acknowledgements), acknowledgements
    assert len(set(ids)) == count, f"job IDs not unique: {ids}"
    print(f"PASS: {count} concurrent clients received queued acknowledgements and unique job IDs")
    print("Job IDs: " + ", ".join(sorted(ids)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
