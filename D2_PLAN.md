# D2 rubric plan and evidence

| D2 rubric area | Implementation in this copy | Evidence to collect |
|---|---|---|
| Complete application functionality | Client submit/ack, FIFO queue, worker registration, execution, result status | End-to-end job log and `test_worker_flow.py` pass |
| Dynamic SDN functionality | Diamond topology; OS-Ken tracks OpenFlow port events, flushes stale route flows, and computes a path over active links | Controller log showing primary route before failure and alternate route after `link s1 s2 down` |
| Challenging scenario / robustness | Primary inter-switch link failure during application operation; adaptive controller uses the alternate path; static controller is the baseline | Completion results and logs for static failure vs adaptive failover |
| Performance evaluation | `benchmark.py` records completion latency, P95 latency, throughput, completion rate, and CSV data | Paired static/adaptive summaries and CSV files |
| Documentation/demo | This README, architecture diagram, reproducible commands, tests | README, architecture, screenshots, and saved benchmark CSVs |

## Reproducible comparison

Use the same VM, host placement, number of jobs, worker count, and task implementation for every run. Restart the server and topology between scenarios. Record these scenarios:

1. `static-normal`: fixed primary path, all links up.
2. `static-after-failure`: take s1-s2 down; record jobs completed before timeout.
3. `adaptive-normal`: adaptive controller, all links up.
4. `adaptive-after-failover`: take s1-s2 down; record successful completion over s1-s3-s4.

Use `benchmark.py` output and CSV for completion rate, average/P95 job completion latency, and throughput. Also record failover time from the controller's link-down log to its first alternate-route log. Do not claim a Mininet result until the scenario is actually run in the Ubuntu VM.

## Current boundaries

- The static-vs-adaptive comparison is intended to demonstrate loss of service on a fixed path versus continued job completion after adaptive route selection.
- Queue/status data are process-local memory; they are not durable across server restarts.
- The worker's work is simulated so demonstrations stay safe and repeatable.
- Mininet and OS-Ken are not available in the Windows authoring environment; their runtime behavior must be verified in the Ubuntu VM.
