#!/usr/bin/env python3
"""Local integration check for submit -> FIFO -> worker -> completion."""
from __future__ import annotations

import json
import socket
import threading
import time

import server
import worker
from common import receive_message, send_message


def submit(host: str, port: int, payload: str) -> dict:
    with socket.create_connection((host, port), timeout=5) as sock:
        send_message(sock, {"type": "submit", "payload": payload})
        response = receive_message(sock)
    if response is None:
        raise AssertionError("server returned no acknowledgement")
    return response


def main() -> int:
    host = "127.0.0.1"
    app = server.ThreadedTCPServer((host, 0), server.JobRequestHandler)
    server.start_scheduler()
    threading.Thread(target=app.serve_forever, daemon=True).start()
    port = app.server_address[1]
    worker_thread = threading.Thread(
        target=worker.start_worker,
        args=("integration-worker", host, port),
        daemon=True,
    )
    worker_thread.start()

    try:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            with server.STATE_LOCK:
                if "integration-worker" in server.WORKERS:
                    break
            time.sleep(0.05)
        else:
            raise AssertionError("worker failed to register")

        payloads = ["first FIFO task", "second FIFO task", "third FIFO task"]
        acknowledgements = [submit(host, port, payload) for payload in payloads]
        ids = [ack.get("job_id") for ack in acknowledgements]
        assert all(ack.get("status") == "queued" for ack in acknowledgements), acknowledgements
        assert len(set(ids)) == len(payloads), ids

        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            with server.STATE_LOCK:
                completed = all(server.JOB_STATUS.get(job_id, {}).get("status") == "completed" for job_id in ids)
            if completed:
                break
            time.sleep(0.05)
        else:
            raise AssertionError("jobs did not all complete before the timeout")

        with server.STATE_LOCK:
            assignment_order = sorted(ids, key=lambda job_id: server.JOB_STATUS[job_id]["assigned_at"])
            assigned_payloads = [server.JOB_STATUS[job_id]["job"]["payload"] for job_id in assignment_order]
        assert assigned_payloads == payloads, assigned_payloads
        print("PASS: worker registered, received three FIFO jobs, and reported all results")
        print("Completed IDs: " + ", ".join(ids))
        return 0
    finally:
        with server.STATE_LOCK:
            connections = list(server.WORKERS.values())
        for connection in connections:
            try:
                connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        app.shutdown()
        app.server_close()
        worker_thread.join(timeout=2)


if __name__ == "__main__":
    raise SystemExit(main())
