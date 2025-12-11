from nodo.routing.routing_table import RoutingTable
from nodo.utils.routing.network import CONNECTED
from pysim_sdk.utils import log
from pysim_sdk.utils.ip_address import ip2str, str2ip
from nodo.utils.routing.message_factory import create_message, create_message_from_args
from nodo.utils.routing.network import ON_GTW_REQ, WITH_NETWORK, Network
from nodo.routing.routing_utils import get_node_subnets
from nodo.utils.routing.peer_messages import PeerMessageType
from nodo.utils.routing.sibling_messages import (
    ProvisionMessage,
    RouteLostMessage,
    SiblDtrUpdateMessage,
    SiblGtwReqMessage,
    SiblGtwWinnerMessage,
    SiblUpdateNodeTableMessage,
    SiblingMessageType,
)


class IternalFordwarder:
    def __init__(self, network: Network) -> None:
        self.ntw = network

    def on_provision(self, message: ProvisionMessage):
        if self.ntw.global_state == WITH_NETWORK:
            log.info(
                "[PROVISION] Home device already provisioned -- skipping new provision"
            )
            # I think here we have to add the backup route
            return

        provider_id = message.provider_id
        network = message.network
        mask = message.mask

        log.info(
            f"[PROVISION] Provisioned {ip2str(network)}/{mask.bit_count()} by `{provider_id}`"
        )
        if network == 167772160:
            self.ntw.dtr = 1

        # Find out my assigned subnet
        # NOTE: this code assumes that the SPI IP of forwarders are 127.0.0.1, .2, .3 and .4
        # Subnets are assigned in the following manner:
        # - Local root node (the provider) will not get an IP block
        # - Home node (127.0.0.5) will get the 00 subnet
        # - Subnets 01, 10 and 11 will be assigned in clockwise direction,
        #   the first one will be assigned to the forwarder in the SPI
        #   loop next to the provider.
        # - As an example, if the provider is 127.0.0.2, then the blocks will
        #   be assigned as follows:
        #   - 127.0.0.3 gets subnet 01
        #   - 127.0.0.4 gets subnet 10
        #   - 127.0.0.1 gets subnet 11

        node_networks, new_mask = get_node_subnets(network, mask)
        new_network = node_networks[self.ntw.orientation]
        self.ntw.node_network = network
        self.ntw.node_network_mask = mask
        self.ntw.my_network = new_network
        self.ntw.my_network_mask = new_mask

        for node_id, node_network in node_networks.items():
            if node_id == self.ntw.orientation:
                self.ntw.output.add_route(new_network, new_mask, "wlan")
            elif node_id == provider_id:
                continue
            else:
                self.ntw.output.add_route(node_network, new_mask, "spi")
        self.ntw.output.enable_ap_mode(self.ntw.my_network, self.ntw.my_network_mask)
        self.ntw.global_state = WITH_NETWORK

    def on_route_lost(self, message: RouteLostMessage):
        routes = message.routes
        for ip, mask in routes:
            prefix_len = mask.bit_count()
            log.info(f"[ROUTE LOST] {ip2str(ip)}/{prefix_len}")
            self.ntw.output.remove_route(ip, mask)

    def on_send_gtw_req(self, message: SiblGtwReqMessage):
        if self.ntw.dtr == 1:
            # I am root
            return
        if self.ntw.global_state == ON_GTW_REQ:
            return

        self.ntw.global_state = ON_GTW_REQ
        self.ntw.dtr = 0
        hag_ips = message.hag_ips

        if not len(hag_ips):
            hag_ips = f"{ip2str(self.ntw.node_network)}/{self.ntw.node_network_mask.bit_count()}"
        else:
            hag_ips = f"{hag_ips} {ip2str(self.ntw.node_network)}/{self.ntw.node_network_mask.bit_count()}"

        message = create_message_from_args(
            PeerMessageType.NEW_GTW_REQUEST, hag_ips=hag_ips
        )
        self.ntw.output.send_peer_message(message.serialize())

    def on_new_gtw_winner(self, message: SiblGtwWinnerMessage):
        # TODO
        # check case where i am root
        if self.ntw.dtr == 1:
            message = create_message_from_args(
                PeerMessageType.NEW_GTW_RESPONSE,
                ext_network=self.ntw.node_network,
                ext_mask=self.ntw.node_network_mask,
                dtr=self.ntw.dtr,
            )
            self.ntw.output.send_peer_message(message.serialize())
            return

        self.ntw.global_state = WITH_NETWORK
        self.ntw.output.switch_default_gateway("spi")
        self.ntw.is_local_root = False

        # self.ntw.output.reset_routing_table()
        # chequear!!!! creo que no hace falta porque por default voy por spi y el que recibio el mensaje del peer va a saber por que se sale por wifi
        # mask = message.mask
        # network = message.network
        # self.ntw.output.add_route(network, mask, "spi")
        ########
        self.ntw.dtr = message.dtr + 1
        # enviar mensaje a mi peer
        message = create_message_from_args(
            PeerMessageType.NEW_GTW_RESPONSE,
            ext_network=self.ntw.node_network,
            ext_mask=self.ntw.node_network_mask,
            dtr=self.ntw.dtr,
        )
        self.ntw.output.send_peer_message(message.serialize())

    def on_sibling_DTR_update(self, message: SiblDtrUpdateMessage):
        peer_dtr = message.dtr
        if peer_dtr == 0:
            # it must be imposible
            log.error("wrong dtr received")
            return
        elif self.ntw.dtr == 0 or peer_dtr < self.ntw.dtr:
            self.ntw.dtr = peer_dtr
            self.ntw.output.switch_default_gateway("spi")
            self.ntw.is_local_root = False
            if self.ntw.local_state == CONNECTED:
                message = create_message_from_args(
                    PeerMessageType.DTR_UPDATE, dtr=self.ntw.dtr
                )
                self.ntw.output.send_peer_message(message.serialize())
        else:
            log.error("worse DTR received")

    def on_node_table_update(self, message: SiblUpdateNodeTableMessage):
        self.ntw.node_routing_table = RoutingTable.from_json(message.table)

    def process_message(self, event_id, payload: dict):
        if event_id == SiblingMessageType.PROVISION:
            message = create_message(SiblingMessageType.PROVISION, payload)
            self.on_provision(message)
        elif event_id == SiblingMessageType.ROUTE_LOST:
            message = create_message(SiblingMessageType.ROUTE_LOST, payload)
            self.on_route_lost(message)
        elif event_id == SiblingMessageType.DTR_UPDATE:
            message = create_message(SiblingMessageType.DTR_UPDATE, payload)
            self.on_sibling_DTR_update(message)
        elif event_id == SiblingMessageType.SEND_NEW_GTW_REQUEST:
            message = create_message(SiblingMessageType.SEND_NEW_GTW_REQUEST, payload)
            self.on_send_gtw_req(message)
        elif event_id == SiblingMessageType.NEW_GTW_WINNER:
            message = create_message(SiblingMessageType.NEW_GTW_WINNER, payload)
            self.on_new_gtw_winner(message)
        elif event_id == SiblingMessageType.UPDATE_NODE_TABLE:
            message = create_message(SiblingMessageType.UPDATE_NODE_TABLE, payload)
            self.on_node_table_update(message)
        else:
            log.error(f"Unknown internal event ID: {event_id}")
