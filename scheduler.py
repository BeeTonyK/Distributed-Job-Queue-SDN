"""Round-robin scheduler that assigns FIFO jobs to registered idle workers."""
from __future__ import annotations

import time
from queue import Empty
from typing import Any

from common import send_message


def scheduler_loop(job_queue, workers, busy_workers, lock, assigned_jobs, job_status) -> None:
    print("[SCHEDULER] Round-robin scheduler started", flush=True)
    next_worker = 0

    while True:
        with lock:
            available = [
                (worker_id, connection)
                for worker_id, connection in workers.items()
                if worker_id not in busy_workers
            ]
            if not available:
                selected = None
                job = None
            else:
                selected = available[next_worker % len(available)]
                try:
                    job = job_queue.get_nowait()
                except Empty:
                    job = None
                if job is not None:
                    worker_id, connection = selected
                    next_worker += 1
                    busy_workers.add(worker_id)
                    assigned_jobs[worker_id] = job
                    job_status[job["job_id"]] = {
                        "status": "assigned",
                        "job": job,
                        "worker_id": worker_id,
                        "assigned_at": time.monotonic(),
                    }

        if job is None or selected is None:
            time.sleep(0.1)
            continue

        worker_id, connection = selected
        try:
            send_message(connection, {
                "type": "job",
                "job_id": job["job_id"],
                "task": job["task"],
            })
            print(f"[SCHEDULER] Assigned {job['job_id']} to {worker_id}", flush=True)
        except (OSError, ConnectionError, ValueError) as exc:
            print(f"[SCHEDULER] Could not send {job['job_id']} to {worker_id}: {exc}", flush=True)
            with lock:
                if workers.get(worker_id) is connection:
                    workers.pop(worker_id, None)
                busy_workers.discard(worker_id)
                returned = assigned_jobs.pop(worker_id, None)
                if returned is not None:
                    job_status[returned["job_id"]] = {"status": "queued", "job": returned}
                    job_queue.put(returned)

        time.sleep(0.05)
