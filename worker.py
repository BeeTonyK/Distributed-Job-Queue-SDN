import socket
import sys
import time
import os

from common import send_message, receive_message

HOST = os.environ.get("TEAM3_SERVER_HOST", "127.0.0.1")
PORT = 5000


def execute_job(task):
    print(f"[WORKER] Executing: {task}")

    time.sleep(2)

    return f"Completed: {task}"


def start_worker(worker_id):

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    sock.connect((HOST, PORT))

    send_message(sock, {
        "type": "register",
        "worker_id": worker_id
    })

    print(f"[WORKER] {worker_id} connected to server")

    try:
        while True:

            job = receive_message(sock)

            if job is None:
                break

            if job.get("type") == "job":

                job_id = job["job_id"]
                task = job["task"]

                result = execute_job(task)

                send_message(sock, {
                    "type": "result",
                    "job_id": job_id,
                    "result": result
                })

    except Exception as e:
        print("[WORKER ERROR]", e)

    finally:
        sock.close()


if __name__ == "__main__":

    worker_id = sys.argv[1] if len(sys.argv) > 1 else "worker1"

    start_worker(worker_id)
