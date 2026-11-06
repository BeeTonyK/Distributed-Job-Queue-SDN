#!/usr/bin/env python3
"""Measure job completion latency and throughput against a running server."""
from __future__ import annotations

import argparse
import csv
import json
import math
import socket
import time
from pathlib import Path

from common import receive_message, send_message


def request(host: str, port: int, message: dict) -> dict:
    with socket.create_connection((host, port), timeout=5) as sock:
        send_message(sock, message)
        response = receive_message(sock)
    if response is None:
        raise ConnectionError("server closed the connection without a reply")
    if response.get("type") == "error":
        raise RuntimeError(response.get("message", "server rejected request"))
    return response


def percentile95(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(0.95 * len(ordered)) - 1)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--label", default="run")
    parser.add_argument("--poll", type=float, default=0.05)
    parser.add_argument("--max-wait", type=float, default=120.0)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()
    if args.count < 1 or args.poll <= 0:
        parser.error("count and poll must be positive")

    records = []
    run_started = time.perf_counter()
    for index in range(args.count):
        submitted = time.perf_counter()
        ack = request(args.host, args.port, {
            "type": "submit",
            "payload": {"task": "benchmark", "label": args.label, "index": index},
        })
        if ack.get("status") != "queued":
            raise RuntimeError(f"job was not queued: {ack}")
        records.append({"job_id": ack["job_id"], "submitted": submitted, "completed": None, "status": "queued"})

    deadline = time.perf_counter() + args.max_wait
    remaining = {record["job_id"] for record in records}
    while remaining and time.perf_counter() < deadline:
        for record in records:
            if record["job_id"] not in remaining:
                continue
            status = request(args.host, args.port, {"type": "status", "job_id": record["job_id"]})
            if status.get("status") == "completed":
                record["completed"] = time.perf_counter()
                record["status"] = "completed"
                remaining.remove(record["job_id"])
        if remaining:
            time.sleep(args.poll)

    for record in records:
        record["completion_seconds"] = (
            record["completed"] - record["submitted"] if record["completed"] is not None else ""
        )
    output = args.output or f"benchmark-{args.label}.csv"
    with Path(output).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["label", "job_id", "status", "completion_seconds"])
        writer.writeheader()
        for record in records:
            writer.writerow({
                "label": args.label,
                "job_id": record["job_id"],
                "status": record["status"],
                "completion_seconds": record["completion_seconds"],
            })

    durations = [record["completion_seconds"] for record in records if record["status"] == "completed"]
    elapsed = time.perf_counter() - run_started
    print(f"Run: {args.label}; completed: {len(durations)}/{args.count}; elapsed: {elapsed:.3f}s")
    if durations:
        print(f"Mean completion latency: {sum(durations) / len(durations):.3f}s")
        print(f"P95 completion latency: {percentile95(durations):.3f}s")
        print(f"Completion throughput: {len(durations) / elapsed:.2f} jobs/s")
    print(f"CSV: {output}")
    return 0 if len(durations) == args.count else 1


if __name__ == "__main__":
    raise SystemExit(main())
