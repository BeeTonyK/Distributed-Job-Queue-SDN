# Team 3 D2 Architecture

```mermaid
flowchart LR
    subgraph Hosts[Mininet hosts]
        C[Client h2]
        S[Job server h1\nTCP :5000]
        W[Worker h3]
    end

    subgraph DataPlane[Open vSwitch data plane]
        SW1[s1]
        SW2[s2]
        SW3[s3]
        SW4[s4]
        SW1 ---|Primary path| SW2
        SW2 --- SW4
        SW1 ---|Backup path| SW3
        SW3 --- SW4
        S --- SW1
        C --- SW1
        W --- SW4
    end

    Ctrl[OS-Ken OpenFlow 1.3 controller]
    Ctrl -. switch control .-> SW1
    Ctrl -. switch control .-> SW2
    Ctrl -. switch control .-> SW3
    Ctrl -. switch control .-> SW4

    C -->|Submit job, receive job ID ACK| S
    S -->|FIFO queue and scheduling| S
    S -->|Assign job| W
    W -->|Completion result| S
    C -->|Poll job status| S
```

## Normal operation

The client submits a job to the TCP server on h1. The server assigns a unique job ID, queues the job, and acknowledges the submission. The scheduler sends queued jobs to registered workers. The worker simulates execution and reports its result; the client-side benchmark polls the server until completion.

## Link failure

Switches s1 and s4 have two paths: s1-s2-s4 and s1-s3-s4. The adaptive controller receives OpenFlow port-state events. When a primary link goes down, it removes route flows and installs routes along the remaining active path when traffic arrives. The static baseline restricts routing to s1-s2-s4 so the same link failure can be compared against adaptive routing.

## D2 verification boundary

The TCP application tests can run on a regular Python installation. The topology and controller require Ubuntu with Mininet, Open vSwitch, and OS-Ken. Save Ubuntu logs and benchmark CSVs as evidence; do not treat this diagram or source code alone as proof that link failover ran successfully.
