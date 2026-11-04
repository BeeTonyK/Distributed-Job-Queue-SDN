# Distributed Job Queue and Worker Management System

A distributed job-processing system built using **TCP Socket Programming, Mininet, and Software-Defined Networking (SDN)**.

The project allows multiple clients to submit jobs to a central server. The server manages incoming jobs through a FIFO queue and distributes them to registered worker nodes for execution. An SDN controller monitors network communication and supports dynamic routing and failure handling.

## Project Objectives

- Enable multiple clients to submit jobs using TCP sockets.
- Generate unique IDs and acknowledgments for submitted jobs.
- Manage submitted jobs using a FIFO queue.
- Register and monitor worker nodes.
- Distribute jobs among available workers.
- Use Mininet to simulate a network topology.
- Use OS-Ken as the SDN controller.
- Explore dynamic routing and failure handling.

## System Architecture

```text
        Client 1       Client 2
            \           /
             \         /
              TCP Socket
                  |
                  v
             Job Server
                  |
                  v
              FIFO Queue
                  |
                  v
           Worker Scheduler
             /         \
            v           v
         Worker 1    Worker 2
             \         /
              \       /
           Mininet Network
                  |
                  v
             OS-Ken SDN
              Controller
```

## Technologies Used

| Technology | Purpose |
|---|---|
| Python | Application development |
| TCP Sockets | Client-server communication |
| Mininet | Network emulation |
| OS-Ken | SDN controller |
| OpenFlow | Switch-controller communication |
| Ubuntu | Development environment |
| Git & GitHub | Version control and collaboration |

## Project Structure

```text
distributed-job-queue-sdn/
│
├── server/
│   └── server.py
│
├── client/
│   └── client.py
│
├── worker/
│   └── worker.py
│
├── controller/
│   └── run_controller.py
│
├── topology/
│   └── topology.py
│
├── common/
│   └── protocol.py
│
├── docs/
│
└── README.md
```

*The structure may be updated as development progresses.*

## Team Members

| Member | Responsibility |
|---|---|
| Bennett | TCP client-server communication and job queue |
| Debayan | Mininet topology and OS-Ken SDN controller |
| Deekshith | Worker management, job execution and
