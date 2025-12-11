# Main function for the central ESP32 device from a root node.
#
# This node does not have a parent, so it will never try to find a sibling.
# Another way to look at this is to consider this as a forwarding node that's
# never in the "searching" state.
#
# The root node is the one who decides which subnetwork will be used for the whole
# mesh network and is the gateway to Internet.
#
# - All the wireless interfaces of the root node are always in AP mode
# - Address negotiation is always won by the root node
# - [FUTURE WORK] More than one root node may exist in the network at the same time but they
#   can't be linked to each other.

import time
from nodo.routing.device_core import DeviceCore
from nodo.routing.routing_table import RoutingTable
from pysim_sdk.utils.ip_address import str2ip
from pysim_sdk.utils import log
from nodo.utils.routing.message_factory import create_message_from_args
from nodo.utils.routing.sibling_messages import SiblingMessageType

ROOT_NETWORK = "10.0.0.0"
ROOT_MASK = "255.0.0.0"
ROOT_PROVISION_MASK = "255.0.0.0"
ROOT_PROVISION_NETWORK = "10.0.0.0"

MSG_SIBL_PROVISION = 2
SIBL_MSG_SEND_NEW_GTW_REQUEST = 4
SIBL_MSG_NEW_GTW_WINNER = 5


class RootCore(DeviceCore):
    def __init__(self):
        super().__init__("root")
        self.gtw_request_tms = None
        self.node_routing_table = RoutingTable("c")

    def on_start(self):
        # We'll assume an Internet connection always active. This means
        # there are no PeerConnected / PeerLost events to handle.
        #
        # Also, this device will be in AP mode, meaning that it will be
        # connected to the Internet gateway and not the other way around.
        #
        # We'll also assume that the Internet gateway is at 192.168.1.1
        #
        # This node handles the following packets:
        #  - From SPI interface (127.0.0.0/24) => forward
        #  - From WLAN interface => NAT & forward

        # Setup LAN
        #  - Default gateway -> Internet / WLAN
        self.output.switch_default_gateway("wlan")

        #  - Root network -> SPI
        self.output.add_route(
            str2ip(ROOT_PROVISION_NETWORK), str2ip(ROOT_PROVISION_MASK), "spi"
        )

        # Provision forwarders
        self.output.broadcast_to_siblings(
            self._generate_provision(
                str2ip(ROOT_PROVISION_NETWORK), str2ip(ROOT_PROVISION_MASK)
            )
        )

    def on_sibling_message(self, message: dict):
        # msg_id = message["id"]
        event_id = SiblingMessageType(message["id"])
        if event_id == SiblingMessageType.SEND_NEW_GTW_REQUEST:
            self.gtw_request_tms = time.time()
            log.info("[ROOT HOME] SEND_NEW_GTW_REQUEST received")
        elif event_id == SiblingMessageType.UPDATE_NODE_TABLE:
            self.node_routing_table = RoutingTable.from_json(message["table"])
        else:
            log.error(f"[ROOT HOME] Unknown or ignored sibling message: {message}")

    def on_tick(self):
        # time.time returns tms in seconds
        if self.gtw_request_tms and time.time() - self.gtw_request_tms > 10:
            log.info(f"[ROOT HOME] ENTRE: tms {self.gtw_request_tms}")
            self.gtw_request_tms = None
            sibling_message = create_message_from_args(
                SiblingMessageType.NEW_GTW_WINNER,
                network=str2ip(ROOT_PROVISION_NETWORK),
                mask=str2ip(ROOT_PROVISION_MASK),
                dtr=1,
            )
            self.output.broadcast_to_siblings(sibling_message.serialize())

    @staticmethod
    def _generate_gtw_winner(network, mask):
        return {
            "id": SIBL_MSG_NEW_GTW_WINNER,
            "dtr": 0,
            "network": network,
            "mask": mask,
        }

    @staticmethod
    def _generate_provision(network, mask):
        # src = 5 => root
        return {
            "id": "PROVISION",
            "provider_id": 5,
            "network": network,
            "mask": mask,
        }

    def on_forward(self, src_ip: str, dst_ip: str):
        path = self.node_routing_table.route(str2ip(src_ip)).interface
        return_path = self.node_routing_table.route(str2ip(dst_ip)).interface
        if path == return_path:
            log.warn(
                f"[ON_FORWARD] Routing loop detected {src_ip} and {dst_ip} route to {path!r}"
            )

    def status(self):
        return "------ NODE ROUTING TABLE ------\n" + str(self.node_routing_table)
