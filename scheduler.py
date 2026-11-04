import time
from common import send_message


def scheduler_loop(job_queue, workers, busy_workers, lock):

    print("[SCHEDULER] Round Robin Scheduler started")

    last_worker = 0

    while True:

        with lock:
            available_workers = [
                (worker_id, conn)
                for worker_id, conn in workers.items()
                if worker_id not in busy_workers
            ]

        if job_queue.empty() or not available_workers:
            time.sleep(0.5)
            continue

        worker_index = last_worker % len(available_workers)

        worker_id, worker_conn = available_workers[worker_index]

        last_worker += 1

        job = job_queue.get()

        try:
            with lock:
                busy_workers.add(worker_id)

            send_message(worker_conn, {
                "type": "job",
                "job_id": job["job_id"],
                "task": job["task"]
            })

            print(
                f"[SCHEDULER] Job {job['job_id']} "
                f"assigned to {worker_id}"
            )

        except Exception as e:
            print("[SCHEDULER ERROR]", e)

            with lock:
                busy_workers.discard(worker_id)
                workers.pop(worker_id, None)

            job_queue.put(job)

        time.sleep(0.5)
