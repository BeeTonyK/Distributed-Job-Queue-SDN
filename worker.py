#!/usr/bin/env python3
"""Register a worker, execute assigned demo tasks, and report results."""
from __future__ import annotations

import argparse
import os
import socket
import time
from typing import Any

from common import receive_message, send_message


DEFAULT_HOST = os.environ.get("TEAM3_SERVER_HOST", "127.0.0.1")
DEFAULT_PORT = int(os.environ.get("TEAM3_SERVER_PORT", "5000"))


def execute_job(task: Any) -> dict[str, Any]:
    print(f"[WORKER] Executing: {task}", flush=True)
    time.sleep(0.5)
    return {"status": "completed", "summary": str(task)}


def start_worker(worker_id: str, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    with socket.create_connection((host, port), timeout=10) as sock:
        sock.settimeout(None)
        send_message(sock, {"type": "register", "worker_id": worker_id})
        response = receive_message(sock)
        if not response or response.get("type") != "registered":
            raise ConnectionError(f"worker registration failed: {response}")
        print(f"[WORKER] Registered as {worker_id} with {host}:{port}", flush=True)

        while True:
            job = receive_message(sock)
            if job is None:
                print("[WORKER] Server disconnected", flush=True)
                return
            if job.get("type") != "job":
                print(f"[WORKER] Ignored unexpected message: {job}", flush=True)
                continue

            result = execute_job(job["task"])
            send_message(sock, {"type": "result", "job_id": job["job_id"], "result": result})
            print(f"[WORKER] Reported completion for {job['job_id']}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("worker_id", nargs="?", default="worker1")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()
    try:
        start_worker(args.worker_id, args.host, args.port)
    except (OSError, ConnectionError, ValueError) as exc:
        parser.exit(1, f"[WORKER ERROR] {exc}\n")


if __name__ == "__main__":
    main()
