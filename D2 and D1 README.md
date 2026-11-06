# Team 3 - D2 Dynamic Job Queue and SDN Failover

This D2 copy builds on the tested D1 app. It keeps the TCP queue and worker flow, adds a job-status protocol for measurement, and changes the network to a diamond with two paths between the server-side and worker-side switches. The adaptive OS-Ken controller tracks OpenFlow port-state changes, deletes stale route flows, and selects a remaining path. A static primary-path runner is included as the comparison baseline.

## Components

- `server.py`, `client.py`, `common.py`: TCP newline-JSON submission, acknowledgements, job status, and worker results.
- `scheduler.py`, `worker.py`: FIFO queue, round-robin dispatch, execution, result reporting, and job requeue after a detected worker disconnect.
- `sdn/topology.py`: four hosts, four switches, and two paths from s1 to s4.
- `sdn/team3_controller.py`: adaptive OpenFlow 1.3 MAC learning, shortest active path selection, and link-event failover.
- `sdn/run_controller.py`: adaptive controller.
- `sdn/run_controller_static.py`: fixed-primary-path comparison baseline.
- `benchmark.py`: completion latency, P95 latency, completion rate, throughput, and CSV output.
- `test_worker_flow.py`, `test_clients.py`: local integration and concurrent-client checks.
- `D2_PLAN.md`: rubric mapping, scenario, measurements, and evidence checklist.

## 1. Check the TCP application

From the project root:

```bash
python3 -m py_compile common.py server.py scheduler.py client.py worker.py benchmark.py test_clients.py test_worker_flow.py sdn/topology.py sdn/team3_controller.py sdn/run_controller.py sdn/run_controller_static.py
python3 test_worker_flow.py
```

The worker-flow test should end with `PASS: worker registered, received three FIFO jobs, and reported all results`.

## 2. Run the D2 SDN demo

Use an Ubuntu VM with Mininet, Open vSwitch, and OS-Ken installed. Run commands from the project root unless the step says otherwise.

### Terminal 1 - adaptive controller

```bash
cd sdn
python3 run_controller.py
```

### Terminal 2 - topology

```bash
sudo mn -c
sudo python3 sdn/topology.py
```

At `mininet>`, check the network:

```text
nodes
pingall
```

Expected: `h1`-`h4`, `s1`-`s4`, and 0% ping loss. In Terminal 1, confirm that all four switches connect.

## 3. Start the server and worker hosts

The topology starts from the project root, so Mininet hosts can use relative project file paths. Run these at `mininet>`:

```text
h1 python3 -u server.py --host 0.0.0.0 --port 5000 > /tmp/team3-server.log 2>&1 &
h3 python3 -u worker.py worker1 --host 10.0.0.1 --port 5000 > /tmp/team3-worker.log 2>&1 &
```

Confirm registration:

```text
h1 sleep 1
h1 cat /tmp/team3-server.log
```

Look for `WORKER_REGISTERED`.

## 4. Measure normal-path performance

At `mininet>` submit ten jobs and measure completion time:

```text
h2 python3 benchmark.py --host 10.0.0.1 --port 5000 --count 10 --label adaptive-normal
```

Expected output includes `completed: 10/10`, mean completion latency, P95 latency, throughput, and a CSV path. The benchmark measures from each job submission until the server reports completion.

## 5. Trigger and measure link failover

Take the primary path down:

```text
link s1 s2 down
```

The adaptive controller should log `LINK DOWN`, clear learned route flows, and on subsequent application traffic log a route via `s1-s3-s4`. Then run:

```text
h2 python3 benchmark.py --host 10.0.0.1 --port 5000 --count 10 --label adaptive-after-failover
```

Expected: jobs complete over the alternate path. Save the controller logs and both benchmark CSV files. Restore the link with `link s1 s2 up` if continuing in the same run.

## 6. Run the static comparison

Stop the Mininet topology with `exit` and stop the controller with Ctrl+C. Start a fresh run using the static controller:

1. Terminal 1: `cd sdn`, then `python3 run_controller_static.py`.
2. Terminal 2: from project root, run `sudo mn -c`, then `sudo python3 sdn/topology.py`.
3. Start the server and worker as above.
4. Run a normal baseline: `h2 python3 benchmark.py --host 10.0.0.1 --port 5000 --count 10 --label static-normal`.
5. At `mininet>`, run `link s1 s2 down`, then `h2 python3 benchmark.py --host 10.0.0.1 --port 5000 --count 10 --label static-after-failure --max-wait 15`.

The static controller intentionally ignores link-state changes and keeps the primary path. After that path fails, some or all benchmark jobs should remain incomplete until the timeout. Compare its completion rate and CSV with the adaptive failover run. Run each scenario from a fresh topology so jobs from the previous run do not carry over.

## 7. Evidence to save

- OS-Ken logs showing switch connections and `LINK DOWN` followed by a route via the alternate path.
- Mininet `pingall` output before the failure.
- Adaptive and static benchmark summaries and CSV files.
- Server and worker logs showing jobs completed after adaptive failover.
- `sudo ovs-vsctl show` and `sudo ovs-ofctl -O OpenFlow13 dump-flows s1` output.

The server queue and status are in memory. The worker's demo task uses a short simulated delay rather than running arbitrary commands from client input. See `D2_PLAN.md` for the evaluation matrix and known test boundaries.
