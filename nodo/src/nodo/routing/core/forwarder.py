from nodo.routing.routing_table import RoutingTable
from nodo.routing.routing_utils import get_node_subnets
from nodo.utils.routing.events import *

# Import enums and classes for types and data structures
from nodo.utils.routing.external_forwarder import ExternalFordwarder
from nodo.utils.routing.internal_forwarder import IternalFordwarder
from nodo.utils.routing.message_factory import create_message_from_args
from nodo.utils.routing.network import Network
from nodo.utils.routing.peer_messages import (
    PeerMessageType,
)
from nodo.utils.routing.sibling_messages import (
    SiblingMessageType,
)
from nodo.routing.device_core import DeviceCore
from pysim_sdk.utils.ip_address import ip2str, str2ip
from pysim_sdk.utils import log

IDS_TABLE = {"n": 1, "e": 2, "s": 3, "w": 4, "c": 5}


class ForwarderCore(DeviceCore):
    def __init__(self, orientation):
        super().__init__(f"fwd-{orientation}")

        self.sibling_event_queue = []
        self.peer_event_queue = []
        self.orientation = orientation
        self.network = None
        self.internal_fordwarder = None
        self.external_fordwarder = None

    def on_start(self):
        self.network = Network(self.orientation, self.output)
        self.internal_fordwarder = IternalFordwarder(self.network)
        self.external_fordwarder = ExternalFordwarder(self.network)

    def on_peer_connected(self, network, mask):
        self.peer_event_queue.append(
            RoutingEvent(EVENT_ON_PEER_CONNECTED, {"mask": mask, "network": network})
        )

    def on_peer_message(self, message: dict):
        self.peer_event_queue.append(
            RoutingEvent(
                EVENT_ON_PEER_MESSAGE,
                message,
            )
        )

    def on_peer_lost(self, network, mask):
        self.peer_event_queue.append(
            RoutingEvent(EVENT_ON_PEER_LOST, {"mask": mask, "network": network})
        )

    def on_sibling_message(self, message: dict):
        self.sibling_event_queue.append(
            RoutingEvent(
                EVENT_ON_SIBLING_MESSAGE,
                message,
            )
        )

    def on_critical_section(self):
        for event in self.sibling_event_queue:
            if event.type == EVENT_ON_SIBLING_MESSAGE:
                msg_id = SiblingMessageType(event.payload["id"])
                # if msg_id == SiblingMessageType.UPDATE_NODE_TABLE:
                #     self.network.node_routing_table = RoutingTable.from_json(
                #         event.payload["table"]
                #     )
                # else:
                self.internal_fordwarder.process_message(msg_id, event.payload)

            else:
                log.error(f"Unknown event type: {event.type}")

        self.sibling_event_queue = []

        for event in self.peer_event_queue:
            if event.type == EVENT_ON_PEER_CONNECTED:
                self.external_fordwarder.process_event(
                    EVENT_ON_PEER_CONNECTED, event.payload
                )
            elif event.type == EVENT_ON_PEER_MESSAGE:
                msg_id = PeerMessageType(event.payload["id"])
                self.external_fordwarder.process_message(msg_id, event.payload)

            elif event.type == EVENT_ON_PEER_LOST:
                self.external_fordwarder.process_event(
                    EVENT_ON_PEER_LOST, event.payload
                )
            else:
                log.error(f"Unknown event type: {event.type}")

        self.peer_event_queue = []

    def __str__(self):
        return (
            "-------- DEVICE STATUS --------\n"
            + f"  orientation = {self.network.orientation}\n"
            + f"  my_wlan_ip = {self.network.my_wlan_ip}\n"
            + f"  is_local_root = {self.network.is_local_root}\n"
            + f"  node_network = {self.network.node_network and ip2str(self.network.node_network)}\n"
            + f"  node_network_mask = {self.network.node_network_mask and ip2str(self.network.node_network_mask)}\n"
            + f"  my_network = {self.network.my_network and ip2str(self.network.my_network)}\n"
            + f"  my_network_mask = {self.network.my_network_mask and ip2str(self.network.my_network_mask)}\n"
            + f"  my_dtr = {self.network.dtr}\n"
            + "--------------------------------\n"
            + "------ NODE ROUTING TABLE ------\n"
            + str(self.network.node_routing_table)
        )

    def status(self):
        return str(self)

    def on_forward(self, src_ip: str, dst_ip: str):
        if str2ip(src_ip) & self.network.node_network_mask == self.network.node_network:
            # Packet came from my node
            return

        if str2ip(dst_ip) & self.network.node_network_mask == self.network.node_network:
            # Packet to my network
            return

        path = self.network.node_routing_table.route(str2ip(dst_ip)).interface
        return_path = self.network.node_routing_table.route(str2ip(src_ip)).interface
        if path == return_path:
            log.warn(
                f"[ON_FORWARD] routing loop detected: {src_ip} and {dst_ip} both route to {path!r}"
            )

    def on_change_default_gateway(self, gw: str):
        if gw == "wlan":
            log.warn(f"[CHANGE_GW] {self.orientation!r} has became local root")
            self.network.node_routing_table.default_gateway.interface = self.orientation
            message = create_message_from_args(
                SiblingMessageType.UPDATE_NODE_TABLE,
                table=self.network.node_routing_table,
            )
            self.output.broadcast_to_siblings(message.serialize())

    def do_forward(self, ip_dst: str):
        return self.network.node_routing_table.route(str2ip(ip_dst)).interface
