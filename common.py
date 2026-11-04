import json


def send_message(sock, data):
    message = json.dumps(data) + "\n"
    sock.sendall(message.encode())


def receive_message(sock):
    buffer = b""

    while True:
        chunk = sock.recv(1)

        if not chunk:
            return None

        if chunk == b"\n":
            break

        buffer += chunk

    return json.loads(buffer.decode())
