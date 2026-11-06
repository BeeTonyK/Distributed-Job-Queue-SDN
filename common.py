"""Small newline-delimited JSON protocol helpers for TCP sockets."""
from __future__ import annotations

import json
import socket
from typing import Any


MAX_MESSAGE_BYTES = 1_000_000


def send_message(sock: socket.socket, data: dict[str, Any]) -> None:
    wire = (json.dumps(data, separators=(",", ":")) + "\n").encode("utf-8")
    if len(wire) > MAX_MESSAGE_BYTES:
        raise ValueError("message exceeds 1 MB limit")
    sock.sendall(wire)


def receive_message(sock: socket.socket) -> dict[str, Any] | None:
    buffer = bytearray()
    while True:
        byte = sock.recv(1)
        if not byte:
            return None if not buffer else _decode(buffer)
        if byte == b"\n":
            return _decode(buffer)
        buffer.extend(byte)
        if len(buffer) >= MAX_MESSAGE_BYTES:
            raise ValueError("message exceeds 1 MB limit")


def _decode(buffer: bytearray) -> dict[str, Any]:
    value = json.loads(buffer.decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError("each message must be a JSON object")
    return value
