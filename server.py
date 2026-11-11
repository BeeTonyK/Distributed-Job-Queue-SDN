import socket
import threading
import queue
import uuid

from common import send_message, receive_message
from scheduler import scheduler_loop

HOST = "0.0.0.0"
PORT = 5000

job_queue = queue.Queue()
workers = {}
busy_workers = set()
lock = threading.Lock()


def handle_connection(conn, address):
    worker_id = None

    try:
        data = receive_message(conn)

        if data is None:
            return

        if data.get("type") == "register":
            worker_id = data.get("worker_id")

            with lock:
                workers[worker_id] = conn

            print(f"[SERVER] Worker registered: {worker_id}")

            while True:
                message = receive_message(conn)

                if message is None:
                    break

                if message.get("type") == "result":
                    print(
                        f"[SERVER] Worker {worker_id} "
                        f"completed job {message.get('job_id')}"
                    )

                    with lock:
                        busy_workers.discard(worker_id)

        elif data.get("type") == "submit":
            job_id = str(uuid.uuid4())[:8]

            job_queue.put({
                "job_id": job_id,
                "task": data.get("task", data.get("payload", ""))
            })

            print(f"[SERVER] Job queued: {job_id}")

            send_message(conn, {
                "status": "queued",
                "job_id": job_id
            })

    except Exception as e:
        print("[SERVER ERROR]", e)

    finally:
        if worker_id:
            with lock:
                workers.pop(worker_id, None)
                busy_workers.discard(worker_id)

            print(f"[SERVER] Worker disconnected: {worker_id}")

        conn.close()


def start_server():
    threading.Thread(
        target=scheduler_loop,
        args=(job_queue, workers, busy_workers, lock),
        daemon=True
    ).start()

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    server.bind((HOST, PORT))
    server.listen()

    print(f"[SERVER] Listening on port {PORT}")

    while True:
        conn, address = server.accept()

        threading.Thread(
            target=handle_connection,
            args=(conn, address),
            daemon=True
        ).start()


if __name__ == "__main__":
    start_server()
