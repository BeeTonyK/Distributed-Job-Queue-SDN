#!/usr/bin/env python3
"""TCP job submission server with a thread-safe in-memory FIFO queue."""
from __future__ import annotations

import argparse
import json
import queue
import socketserver
import threading
import uuid
from datetime import datetime, timezone
from typing import Any


class JobQueue:
    def __init__(self) -> None:
        self.items: queue.Queue[dict[str, Any]] = queue.Queue()
        self._counter = 0
        self._lock = threading.Lock()

    def submit(self, payload: Any, client: str) -> dict[str, Any]:
        with self._lock:
            self._counter += 1
            job_id = f"job-{self._counter:06d}"
            job = {
                "job_id": job_id,
                "payload": payload,
                "client": client,
                "submitted_at": datetime.now(timezone.utc).isoformat(),
            }
            self.items.put(job)
            return job


JOBS = JobQueue()


class JobRequestHandler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        # One newline-delimited JSON request per TCP connection.
        raw = self.rfile.readline(1_000_001)
        if not raw:
            return
        try:
            request = json.loads(raw.decode("utf-8"))
            if not isinstance(request, dict) or request.get("type") != "submit":
                raise ValueError("request must be an object with type 'submit'")
            if "payload" not in request:
                raise ValueError("request is missing 'payload'")
            job = JOBS.submit(request["payload"], self.client_address[0])
            response = {"type": "ack", "status": "queued", **job}
            print(f"QUEUED {job['job_id']} from {self.client_address[0]}", flush=True)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            response = {"type": "error", "status": "rejected", "message": str(exc)}
        self.wfile.write((json.dumps(response, separators=(",", ":")) + "\n").encode("utf-8"))


class ThreadedTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="0.0.0.0", help="interface to listen on")
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()
    with ThreadedTCPServer((args.host, args.port), JobRequestHandler) as server:
        print(f"Job server listening on {args.host}:{args.port}", flush=True)
        print("Jobs are acknowledged when added to the in-memory FIFO queue.", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nStopping job server.", flush=True)


if __name__ == "__main__":
    main()
