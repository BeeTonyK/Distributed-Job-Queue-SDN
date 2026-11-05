# Team 3 - SDN Project

## My Work - Deekshith

### 1. Environment
- Ubuntu running in VirtualBox
- Mininet
- Open vSwitch
- OS-Ken SDN Controller
- OpenFlow 1.3

### 2. Network Architecture
- One OVS switch: s1
- Two Mininet hosts: h1 and h2
- Controller address: 127.0.0.1
- OpenFlow port: 6653

### 3. Controller Files
- team3_controller.py
- run_controller.py

### 4. Testing
- Mininet pingall test
- OVS flow-table verification
- Controller connection verification

### 5. Screenshots
See the screenshots folder for:
- architecture.png
- controller_code.png
- controller_connection.png
- flow_table.png
- pingall.png

### 6. Result
The controller connection was verified.
The Mininet pingall test reported 0% packet loss.
OpenFlow 1.3 flow entries were observed on switch s1.
