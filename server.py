#!/usr/bin/env python3
"""TCP job server: accept client jobs, register workers, and track completion."""
from __future__ import annotations

import argparse
import json
import queue
import socketserver
import threading
from datetime import datetime, timezone
from typing import Any

from common import receive_message, send_message
from scheduler import scheduler_loop


class JobQueue:
    """Sequential IDs and a thread-safe FIFO queue."""

    def __init__(self) -> None:
        self.items: queue.Queue[dict[str, Any]] = queue.Queue()
        self.counter = 0

    def submit(self, payload: Any, client_ip: str) -> dict[str, Any]:
        self.counter += 1
        job_id = f"job-{self.counter:06d}"
        return {
            "job_id": job_id,
            "payload": payload,
            "task": payload,
            "client": client_ip,
            "submitted_at": datetime.now(timezone.utc).isoformat(),
        }


JOBS = JobQueue()
WORKERS: dict[str, Any] = {}
BUSY_WORKERS: set[str] = set()
ASSIGNED_JOBS: dict[str, dict[str, Any]] = {}
JOB_STATUS: dict[str, dict[str, Any]] = {}
STATE_LOCK = threading.RLock()


def _send_error(sock: Any, message: str) -> None:
    try:
        send_message(sock, {"type": "error", "status": "rejected", "message": message})
    except (OSError, ValueError):
        pass


class JobRequestHandler(socketserver.BaseRequestHandler):
    """Client sockets submit one request; worker sockets remain open."""

    def handle(self) -> None:
        try:
            request = receive_message(self.request)
            if request is None:
                return
            message_type = request.get("type")
            if message_type == "submit":
                self._submit(request)
            elif message_type == "register":
                self._serve_worker(request)
            elif message_type == "status":
                self._status(request)
            else:
                _send_error(self.request, "type must be 'submit', 'status', or 'register'")
        except (ConnectionError, OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            print(f"[SERVER] Connection error from {self.client_address[0]}: {exc}", flush=True)

    def _submit(self, request: dict[str, Any]) -> None:
        if "payload" not in request:
            _send_error(self.request, "request is missing 'payload'")
            return

        with STATE_LOCK:
            job = JOBS.submit(request["payload"], self.client_address[0])
            JOB_STATUS[job["job_id"]] = {"status": "queued", "job": job}
            JOBS.items.put(job)

        send_message(self.request, {"type": "ack", "status": "queued", **job})
        print(f"[SERVER] QUEUED {job['job_id']} from {self.client_address[0]}", flush=True)

    def _status(self, request: dict[str, Any]) -> None:
        job_id = request.get("job_id")
        if not isinstance(job_id, str):
            _send_error(self.request, "status request requires a job_id")
            return
        with STATE_LOCK:
            current = JOB_STATUS.get(job_id)
            if current is None:
                response = {"type": "status", "job_id": job_id, "status": "unknown"}
            else:
                response = {
                    "type": "status",
                    "job_id": job_id,
                    "status": current["status"],
                    "worker_id": current.get("worker_id"),
                    "result": current.get("result"),
                }
        send_message(self.request, response)

    def _serve_worker(self, request: dict[str, Any]) -> None:
        worker_id = request.get("worker_id")
        if not isinstance(worker_id, str) or not worker_id.strip():
            _send_error(self.request, "register requires a non-empty worker_id")
            return

        with STATE_LOCK:
            if worker_id in WORKERS:
                _send_error(self.request, f"worker '{worker_id}' is already connected")
                return
            # Send registration confirmation before the scheduler can use this socket.
            send_message(self.request, {"type": "registered", "worker_id": worker_id})
            WORKERS[worker_id] = self.request

        print(f"[SERVER] WORKER_REGISTERED {worker_id} from {self.client_address[0]}", flush=True)
        try:
            while True:
                message = receive_message(self.request)
                if message is None:
                    break
                if message.get("type") != "result":
                    print(f"[SERVER] Ignored unexpected message from {worker_id}", flush=True)
                    continue

                job_id = message.get("job_id")
                with STATE_LOCK:
                    assigned = ASSIGNED_JOBS.get(worker_id)
                    if assigned is None or assigned["job_id"] != job_id:
                        print(f"[SERVER] Ignored unexpected result from {worker_id}: {job_id}", flush=True)
                        continue
                    previous = JOB_STATUS.get(job_id, {})
                    JOB_STATUS[job_id] = {
                        "status": "completed",
                        "job": assigned,
                        "worker_id": worker_id,
                        "result": message.get("result"),
                        "completed_at": datetime.now(timezone.utc).isoformat(),
                        "assigned_at": previous.get("assigned_at"),
                    }
                    ASSIGNED_JOBS.pop(worker_id, None)
                    BUSY_WORKERS.discard(worker_id)
                print(f"[SERVER] COMPLETED {job_id} by {worker_id}: {message.get('result')}", flush=True)
        finally:
            # Retry work if the worker disconnects before reporting a result.
            with STATE_LOCK:
                if WORKERS.get(worker_id) is self.request:
                    WORKERS.pop(worker_id, None)
                BUSY_WORKERS.discard(worker_id)
                abandoned = ASSIGNED_JOBS.pop(worker_id, None)
                if abandoned is not None:
                    JOB_STATUS[abandoned["job_id"]] = {"status": "queued", "job": abandoned}
                    JOBS.items.put(abandoned)
            print(f"[SERVER] WORKER_DISCONNECTED {worker_id}", flush=True)


class ThreadedTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def start_scheduler() -> threading.Thread:
    thread = threading.Thread(
        target=scheduler_loop,
        args=(JOBS.items, WORKERS, BUSY_WORKERS, STATE_LOCK, ASSIGNED_JOBS, JOB_STATUS),
        daemon=True,
        name="job-scheduler",
    )
    thread.start()
    return thread


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()

    start_scheduler()
    with ThreadedTCPServer((args.host, args.port), JobRequestHandler) as server:
        print(f"Job server listening on {args.host}:{server.server_address[1]}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\n[SERVER] Stopping", flush=True)


if __name__ == "__main__":
    main()
