#!/usr/bin/env python3
"""Learning switch with shortest-path forwarding and link-failure recovery."""
from __future__ import annotations

import os
import time
from collections import deque

from os_ken.base import app_manager
from os_ken.controller import ofp_event
from os_ken.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from os_ken.lib.packet import ethernet, packet
from os_ken.lib.packet import ether_types
from os_ken.ofproto import ofproto_v1_3


# (switch A, switch B): (A's inter-switch port, B's inter-switch port)
LINK_PORTS = {
    (1, 2): (3, 1),
    (2, 4): (2, 3),
    (1, 3): (4, 1),
    (3, 4): (2, 4),
}
ACCESS_PORTS = {1: {1, 2}, 4: {1, 2}}
PRIMARY_PATH_EDGES = {(1, 2), (2, 4)}
ROUTE_COOKIE = 0xD2F1000000000001
ROUTE_COOKIE_MASK = 0xFFFFFFFFFFFFFFFF


def edge_key(a: int, b: int) -> tuple[int, int]:
    return (a, b) if a < b else (b, a)


class Team3Controller(app_manager.OSKenApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.datapaths = {}
        self.host_locations: dict[str, tuple[int, int]] = {}
        self.link_up = {edge_key(*edge): True for edge in LINK_PORTS}
        self.port_to_edge = {}
        for edge, ports in LINK_PORTS.items():
            self.port_to_edge[(edge[0], ports[0])] = edge_key(*edge)
            self.port_to_edge[(edge[1], ports[1])] = edge_key(*edge)
        self.static_baseline = os.environ.get("TEAM3_STATIC_BASELINE") == "1"
        self.logger.info(
            "TEAM 3 %s controller started",
            "STATIC BASELINE" if self.static_baseline else "ADAPTIVE",
        )

    def _neighbors(self, switch: int):
        for (a, b), _ports in LINK_PORTS.items():
            edge = edge_key(a, b)
            if self.static_baseline and edge not in PRIMARY_PATH_EDGES:
                continue
            if not self.link_up.get(edge, False):
                continue
            if switch == a:
                yield b
            elif switch == b:
                yield a

    def _path(self, source: int, destination: int) -> list[int] | None:
        if source == destination:
            return [source]
        pending = deque([source])
        previous = {source: None}
        while pending:
            current = pending.popleft()
            for neighbor in sorted(self._neighbors(current)):
                if neighbor in previous:
                    continue
                previous[neighbor] = current
                if neighbor == destination:
                    pending.clear()
                    break
                pending.append(neighbor)
        if destination not in previous:
            return None
        path = [destination]
        while path[-1] != source:
            path.append(previous[path[-1]])
        return list(reversed(path))

    def _port_between(self, source: int, destination: int) -> int:
        edge = edge_key(source, destination)
        ports = LINK_PORTS[edge]
        return ports[0] if source == edge[0] else ports[1]

    def _flood_tree_edges(self) -> set[tuple[int, int]]:
        tree = set()
        visited = {1}
        pending = deque([1])
        while pending:
            switch = pending.popleft()
            for neighbor in sorted(self._neighbors(switch)):
                edge = edge_key(switch, neighbor)
                if neighbor not in visited:
                    visited.add(neighbor)
                    tree.add(edge)
                    pending.append(neighbor)
        return tree

    def _flood_ports(self, switch: int) -> set[int]:
        ports = set(ACCESS_PORTS.get(switch, set()))
        for edge in self._flood_tree_edges():
            if switch == edge[0]:
                ports.add(LINK_PORTS[edge][0])
            elif switch == edge[1]:
                ports.add(LINK_PORTS[edge][1])
        return ports

    def _install_path(self, source_mac: str, destination_mac: str):
        source_location = self.host_locations[source_mac]
        destination_location = self.host_locations[destination_mac]
        source_switch, source_port = source_location
        destination_switch, destination_port = destination_location
        path = self._path(source_switch, destination_switch)
        if path is None:
            self.logger.warning("No active path from s%d to s%d", source_switch, destination_switch)
            return None

        output_ports = {}
        for index, switch in enumerate(path):
            datapath = self.datapaths.get(switch)
            if datapath is None:
                return None
            if index == 0:
                in_port = source_port
            else:
                in_port = self._port_between(path[index - 1], switch)
            if index == len(path) - 1:
                out_port = destination_port
            else:
                out_port = self._port_between(switch, path[index + 1])
            output_ports[switch] = out_port
            parser = datapath.ofproto_parser
            match = parser.OFPMatch(in_port=in_port, eth_dst=destination_mac)
            actions = [parser.OFPActionOutput(out_port)]
            instructions = [parser.OFPInstructionActions(datapath.ofproto.OFPIT_APPLY_ACTIONS, actions)]
            datapath.send_msg(parser.OFPFlowMod(
                datapath=datapath,
                cookie=ROUTE_COOKIE,
                priority=20,
                match=match,
                instructions=instructions,
                idle_timeout=120,
            ))
        self.logger.info("ROUTE %s -> %s via %s", source_mac, destination_mac, "-".join(f"s{x}" for x in path))
        return output_ports

    def _flood_packet(self, message, in_port: int) -> None:
        datapath = message.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        actions = [
            parser.OFPActionOutput(port)
            for port in sorted(self._flood_ports(datapath.id))
            if port != in_port
        ]
        data = None if message.buffer_id != ofproto.OFP_NO_BUFFER else message.data
        datapath.send_msg(parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=message.buffer_id,
            in_port=in_port,
            actions=actions,
            data=data,
        ))

    def _flush_routes(self) -> None:
        for datapath in self.datapaths.values():
            ofproto = datapath.ofproto
            parser = datapath.ofproto_parser
            datapath.send_msg(parser.OFPFlowMod(
                datapath=datapath,
                cookie=ROUTE_COOKIE,
                cookie_mask=ROUTE_COOKIE_MASK,
                table_id=ofproto.OFPTT_ALL,
                command=ofproto.OFPFC_DELETE,
                out_port=ofproto.OFPP_ANY,
                out_group=ofproto.OFPG_ANY,
                match=parser.OFPMatch(),
            ))

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, event) -> None:
        datapath = event.msg.datapath
        switch_id = datapath.id
        self.datapaths[switch_id] = datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
        instructions = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        datapath.send_msg(parser.OFPFlowMod(
            datapath=datapath,
            priority=0,
            match=parser.OFPMatch(),
            instructions=instructions,
        ))
        self.logger.info("SWITCH CONNECTED: s%d", switch_id)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, event) -> None:
        message = event.msg
        datapath = message.datapath
        switch_id = datapath.id
        in_port = message.match["in_port"]
        parsed = packet.Packet(message.data)
        ethernet_header = parsed.get_protocol(ethernet.ethernet)
        if ethernet_header is None or ethernet_header.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        if in_port in ACCESS_PORTS.get(switch_id, set()):
            self.host_locations[ethernet_header.src] = (switch_id, in_port)

        destination_location = self.host_locations.get(ethernet_header.dst)
        if destination_location is None:
            self._flood_packet(message, in_port)
            return

        # Source location is learned only on an access port, so do not mistake
        # a transit PacketIn for the host's attachment point.
        source_location = self.host_locations.get(ethernet_header.src)
        if source_location is None:
            self._flood_packet(message, in_port)
            return

        outputs = self._install_path(ethernet_header.src, ethernet_header.dst)
        out_port = outputs.get(switch_id) if outputs else None
        if out_port is None:
            self._flood_packet(message, in_port)
            return
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        data = None if message.buffer_id != ofproto.OFP_NO_BUFFER else message.data
        datapath.send_msg(parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=message.buffer_id,
            in_port=in_port,
            actions=[parser.OFPActionOutput(out_port)],
            data=data,
        ))

    @set_ev_cls(ofp_event.EventOFPPortStatus, MAIN_DISPATCHER)
    def port_status_handler(self, event) -> None:
        message = event.msg
        datapath = message.datapath
        switch_id = datapath.id
        port_no = message.desc.port_no
        edge = self.port_to_edge.get((switch_id, port_no))
        if edge is None:
            return
        if self.static_baseline:
            self.logger.warning("STATIC BASELINE: ignoring link event on s%d port %d", switch_id, port_no)
            return

        ofproto = datapath.ofproto
        link_down = (
            message.reason == ofproto.OFPPR_DELETE
            or bool(message.desc.state & ofproto.OFPPS_LINK_DOWN)
            or bool(message.desc.config & ofproto.OFPPC_PORT_DOWN)
        )
        is_up = not link_down
        if self.link_up.get(edge) == is_up:
            return

        self.link_up[edge] = is_up
        self._flush_routes()
        state = "UP" if is_up else "DOWN"
        self.logger.warning(
            "LINK %s epoch=%.6f: s%d port %d <-> s%d; clearing learned routes",
            state, time.time(), switch_id, port_no, edge[1] if switch_id == edge[0] else edge[0],
        )
        self.logger.info("ACTIVE LINKS: %s", sorted(edge for edge, up in self.link_up.items() if up))
