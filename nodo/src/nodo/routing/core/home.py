from nodo.routing.device_core import DeviceCore
from nodo.routing.routing_table import RoutingTable
from nodo.routing.routing_utils import get_node_subnets
from pysim_sdk.utils.ip_address import ip2str
from pysim_sdk.utils import log
from nodo.utils.routing.message_factory import create_message_from_args
from nodo.utils.routing.sibling_messages import SiblingMessageType

SIBL_MSG_PROVISION = 2


class HomeCore(DeviceCore):
    def __init__(self):
        super().__init__("home")

        self.node_routing_table = RoutingTable("c")
        self.is_provisioned = False
        self.provision_received = None

    def on_sibling_message(self, message: dict):
        if message["id"] == "PROVISION":
            self.provision_received = message
        elif message["id"] == "UPDATE_NODE_TABLE":
            self.node_routing_table = RoutingTable.from_json(message["table"])
        else:
            log.error(f"[HOME] Unknown or ignored sibling message: {message}")

    def on_critical_section(self):
        if provision := self.provision_received:
            self.provision_received = None
            self._on_provision(provision)

    def _on_provision(self, message):
        if self.is_provisioned:
            log.info(
                "[PROVISION] Home device already provisioned -- skipping new provision"
            )
            return

        provider_id, network, mask = (
            message["provider_id"],
            message["network"],
            message["mask"],
        )
        log.info(
            f"[PROVISION] Provisioned {ip2str(network)}/{mask.bit_count()} by {provider_id}"
        )

        assigned_block = 5
        node_networks, new_mask = get_node_subnets(network, mask)
        new_network = node_networks[assigned_block]

        for node_id, node_network in node_networks.items():
            if node_id == assigned_block:
                self.output.add_route(new_network, new_mask, "wlan")
            elif node_id == provider_id:
                continue
            else:
                self.output.add_route(node_network, new_mask, "spi")
        self.output.enable_ap_mode(new_network, new_mask)
        self.is_provisioned = True

        self.node_routing_table.add_route(new_network, new_mask.bit_count(), "c")
        sibl_message = create_message_from_args(
            SiblingMessageType.UPDATE_NODE_TABLE, table=self.node_routing_table
        )
        self.output.broadcast_to_siblings(sibl_message.serialize())

    def status(self):
        return "------ NODE ROUTING TABLE ------\n" + str(self.node_routing_table)
