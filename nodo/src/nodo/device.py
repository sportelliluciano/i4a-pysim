import json
import time
import threading

from scapy.all import IP, ICMP, UDP, raw

from pysim_sdk.utils import log
from pysim_sdk.utils.ip_address import str2ip, ip2str
from pysim_sdk.nic.events import InterfaceEvent

from nodo.routing.device_output import DeviceOutput
from nodo.routing.routing_table import RoutingTable


SIBLINGS_UDP_PORT = 39999

TICK_PERIOD_SECS = 1.0


class Device(DeviceOutput):
    def __init__(self, orientation: str, input_queue, spi_if, wlan_if, core, sync):
        self.name = None
        self.orientation = orientation
        self.input_queue = input_queue
        self.spi_if = spi_if
        self.wlan_if = wlan_if
        self.routing_table = RoutingTable(spi_if)
        self.routing_table.add_route(str2ip("127.0.0.0"), 24, spi_if, static=True)
        self.peer_ip = None
        self.observer = None
        self.sync = sync
        self.sync.register_output(self)
        self.core = core
        self.core.register_output(self)

    def main(self):
        self.name = threading.current_thread().name
        with self.wlan_if, self.spi_if:
            self.observer.event("on_start")
            self.core.on_start()
            self.request_critical_section()

            for event in self.input_queue.events_stream(
                max_block_time=TICK_PERIOD_SECS
            ):
                if event.type == InterfaceEvent.PacketReceived:
                    self._on_packet_received(event)
                elif event.type == InterfaceEvent.PeerConnected:
                    self._on_peer_connected(event)
                elif event.type == InterfaceEvent.PeerLost:
                    self._on_peer_lost(event)
                elif event.type == InterfaceEvent.Tick:
                    self._on_tick(event)
                else:
                    log.info(f"Unknown event: {event}")

                time.sleep(0.001)

            log.info("No more events -- device thread finished")

    def status(self):
        return {
            "orientation": self.orientation,
            "events": self.input_queue.status(),
            "interfaces": {
                "spi": self.spi_if.status(),
                "wlan": self.wlan_if.status(),
            },
            "routing_table": self.routing_table.status(),
            "peer_ip": self.peer_ip,
            "core": self.core.status(),
        }

    def stop(self):
        self.input_queue.put(None)

    @staticmethod
    def _ip4_chksum_match(packet):
        packet_chksum = packet[IP].chksum
        del packet[IP].chksum
        expected_chksum = IP(raw(packet)).chksum
        return packet_chksum == expected_chksum

    def _on_packet_received(self, event):
        packet = IP(event.payload)
        if not self._ip4_chksum_match(packet):
            # log.warn(f"[LWIP] Dropping packet {packet} -- chksum mismatch")
            return

        if packet.dst == self.wlan_if.ip_addr:
            if ICMP in packet and packet[ICMP].type == 2:
                json_payload = json.loads(packet[ICMP].load.decode("utf-8"))
                self.observer.event("on_peer_message", **json_payload)
                self.core.on_peer_message(json_payload)
                self.request_critical_section()
        elif packet.dst == self.spi_if.ip_addr:
            if UDP in packet and packet.dport == SIBLINGS_UDP_PORT:
                self._on_sibling_message(packet.load)
        else:
            self._on_forward(packet)

    def _on_peer_connected(self, event):
        wlan_ip, wlan_mask, peer_ip = event.payload

        self.peer_ip = ip2str(peer_ip)

        self.routing_table.add_route(
            wlan_ip & wlan_mask, wlan_mask.bit_count(), self.wlan_if
        )
        self.observer.event(
            "on_peer_connected", network=wlan_ip & wlan_mask, mask=wlan_mask
        )
        self.core.on_peer_connected(wlan_ip & wlan_mask, wlan_mask)
        self.request_critical_section()

    def _on_peer_lost(self, event):
        wlan_ip, wlan_mask, peer_ip = event.payload

        self.peer_ip = None

        self.routing_table.remove_route(wlan_ip & wlan_mask, wlan_mask.bit_count())
        self.observer.event("on_peer_lost", network=wlan_ip & wlan_mask, mask=wlan_mask)
        self.core.on_peer_lost(wlan_ip & wlan_mask, wlan_mask)
        self.request_critical_section()

    def _on_sibling_message(self, payload: bytes):
        if payload[:1] == self.orientation.encode("ascii"):
            # Broadcast complete
            return

        self.spi_if.send_packet(
            raw(
                IP(src=self.spi_if.ip_addr, dst=self.spi_if.next_hop_ip_addr)
                / UDP(sport=SIBLINGS_UDP_PORT, dport=SIBLINGS_UDP_PORT)
                / payload
            )
        )

        json_payload = json.loads(payload[1:].decode("utf-8"))

        if not self.sync.on_sibling_message(json_payload):
            self.observer.event("on_sibling_message", **json_payload)
            self.core.on_sibling_message(json_payload)
            self.request_critical_section()

    def _on_forward(self, packet):
        packet.ttl -= 1
        packet.chksum = None
        if packet.ttl <= 0:
            log.warn(f"[FORWARD] Discarding {packet} -- TTL=0")
            return

        self.core.on_forward(packet.src, packet.dst)

        if path := self.core.do_forward(packet.dst):
            # Global routing table knows where to go
            if not packet.src.startswith("127.") and path == self.orientation:
                log.info(f"[FORWARD] {packet} through wlan")
                self.wlan_if.send_packet(raw(packet))
            else:
                self.spi_if.send_packet(raw(packet))
        else:
            # Otherwise, use legacy routing table (deprecated)
            if output_if := self.routing_table.route(str2ip(packet.dst)):
                if IP not in packet:
                    log.warn(f"[FORWARD] unknown payload: {raw(packet)}")
                    return

                log.info(f"[FORWARD] {packet} through {output_if}")
                output_if.interface.send_packet(raw(packet))
            else:
                log.info("[FORWARD] No route to host for dst_addr = %s", packet.dst)

    def _on_tick(self, _):
        if self.core.on_tick():
            self.request_critical_section()

    def send_peer_message(self, message: dict):
        if self.peer_ip is not None:
            self.observer.event("send_peer_message", **message)
            self.wlan_if.send_packet(
                raw(
                    IP(src=self.wlan_if.ip_addr, dst=self.peer_ip)
                    / ICMP(type=2, code=0)
                    / json.dumps(message).encode("utf-8")
                )
            )

    def broadcast_to_siblings(self, message: dict) -> bool:
        if message["id"] not in ("request-token", "token-grant"):
            self.observer.event("broadcast_to_siblings", **message)
        self.spi_if.send_packet(
            raw(
                IP(src=self.spi_if.ip_addr, dst=self.spi_if.next_hop_ip_addr)
                / UDP(sport=SIBLINGS_UDP_PORT, dport=SIBLINGS_UDP_PORT)
                / (
                    self.orientation.encode("ascii")
                    + json.dumps(message).encode("utf-8")
                )
            )
        )
        return True

    def enable_ap_mode(self, network: int, mask: int):
        self.observer.event("enable_ap_mode", network=network, mask=mask)
        self.wlan_if.enable_ap_mode(network, mask)

    def switch_default_gateway(self, iface: str):
        self.observer.event("switch_default_gateway", iface=iface)
        self.routing_table.switch_default_gateway(self._get_if_by_name(iface))
        self.core.on_change_default_gateway(iface)

    def add_route(self, network: int, mask: int, iface: str):
        self.observer.event("add_route", network=network, mask=mask, iface=iface)
        self.routing_table.add_route(
            network, mask.bit_count(), self._get_if_by_name(iface)
        )

    def remove_route(self, network: int, mask: int):
        self.observer.event("remove_route", network=network, mask=mask)
        self.routing_table.remove_route(network, mask.bit_count())

    def reset_routing_table(self):
        self.observer.event("reset_routing_table")
        self.routing_table.reset()
        self.routing_table.add_route(str2ip("127.0.0.0"), 24, self.spi_if, static=True)

    def remove_routes_for_interface(self, iface: str):
        self.observer.event("remove_routes_for_interface", iface=iface)
        return self.routing_table.remove_routes_for_interface(
            self._get_if_by_name(iface)
        )

    def _get_if_by_name(self, iface: str):
        if iface == "spi":
            return self.spi_if
        elif iface == "wlan":
            return self.wlan_if

        raise ValueError(f"Invalid interface name: `{iface}`")

    def request_critical_section(self):
        self.observer.request_critical_section()
        return self.sync.request_critical_section()

    def on_critical_section(self):
        self.observer.enter_critical_section()
        self.core.on_critical_section()
        self.observer.exit_critical_section()

    def event(self, *args, **kwargs):
        return self.observer.event(*args, **kwargs)
