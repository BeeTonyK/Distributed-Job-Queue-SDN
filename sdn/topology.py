#!/usr/bin/env python3
"""Redundant four-switch Mininet topology for link-failure failover tests."""
from __future__ import annotations

import os

from mininet.cli import CLI
from mininet.log import info, setLogLevel
from mininet.net import Mininet
from mininet.node import OVSSwitch, RemoteController
from mininet.topo import Topo


class Team3D2Topo(Topo):
    def build(self) -> None:
        switches = {
            name: self.addSwitch(name, dpid=f"{number:016x}", protocols="OpenFlow13")
            for number, name in ((1, "s1"), (2, "s2"), (3, "s3"), (4, "s4"))
        }
        hosts = {
            name: self.addHost(name, ip=f"10.0.0.{number}/8")
            for number, name in ((1, "h1"), (2, "h2"), (3, "h3"), (4, "h4"))
        }

        # Access ports are fixed for the controller: h1/h2 on s1, h3/h4 on s4.
        self.addLink(hosts["h1"], switches["s1"], port2=1)
        self.addLink(hosts["h2"], switches["s1"], port2=2)
        self.addLink(hosts["h3"], switches["s4"], port2=1)
        self.addLink(hosts["h4"], switches["s4"], port2=2)

        # Two equal-cost paths between s1 and s4: via s2 or via s3.
        self.addLink(switches["s1"], switches["s2"], port1=3, port2=1)
        self.addLink(switches["s2"], switches["s4"], port1=2, port2=3)
        self.addLink(switches["s1"], switches["s3"], port1=4, port2=1)
        self.addLink(switches["s3"], switches["s4"], port1=2, port2=4)


def start_network() -> None:
    net = Mininet(
        topo=Team3D2Topo(),
        controller=None,
        switch=OVSSwitch,
        autoSetMacs=True,
    )
    net.addController(
        "c0",
        controller=RemoteController,
        ip=os.environ.get("TEAM3_CONTROLLER_IP", "127.0.0.1"),
        port=int(os.environ.get("TEAM3_CONTROLLER_PORT", "6653")),
    )
    info("*** Starting Team 3 D2 redundant-path topology\n")
    net.start()
    info("*** Network started; use nodes, pingall, and link s1 s2 down/up\n")
    try:
        CLI(net)
    finally:
        net.stop()


if __name__ == "__main__":
    setLogLevel("info")
    start_network()
