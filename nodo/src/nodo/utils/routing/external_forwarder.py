from nodo.routing.routing_utils import get_node_subnets
from pysim_sdk.utils import log
from pysim_sdk.utils.ip_address import ip2str, str2ip
from nodo.utils.routing.events import EVENT_ON_PEER_CONNECTED, EVENT_ON_PEER_LOST
from nodo.utils.routing.message_factory import create_message, create_message_from_args
from nodo.utils.routing.network import (
    CONNECTED,
    NOT_CONNECTED,
    ON_GTW_REQ,
    WITH_NETWORK,
    WITHOUT_NETWORK,
    Network,
)
from nodo.utils.routing.peer_messages import (
    DtrUpdateMessage,
    GtwReqMessage,
    GtwRespMessage,
    HandshakeMessage,
    OnConnectedMessage,
    PeerLostMessage,
    PeerMessageType,
)
from nodo.utils.routing.sibling_messages import (
    SiblingMessageType,
)


class ExternalFordwarder:
    def __init__(self, network: Network) -> None:
        self.ntw = network

    def on_peer_connected(self, message: OnConnectedMessage):
        self.ntw.local_state = CONNECTED
        handshake_message = create_message_from_args(
            PeerMessageType.HANDSHAKE,
            ext_network=self.ntw.node_network or 0,
            ext_mask=self.ntw.node_network_mask or 0,
            prov_network=self.ntw.my_network or 0,
            prov_mask=self.ntw.my_network_mask or 0,
            dtr=self.ntw.dtr or 0,
        )
        orientation = {1: "n", 2: "e", 3: "s", 4: "w", 5: "c"}[self.ntw.orientation]
        self.ntw.output.send_peer_message(handshake_message.serialize())
        self.ntw.node_routing_table.add_route(
            message.network,
            message.mask.bit_count(),
            orientation,
        )
        sibl_message = create_message_from_args(
            SiblingMessageType.UPDATE_NODE_TABLE, table=self.ntw.node_routing_table
        )
        self.ntw.output.broadcast_to_siblings(sibl_message.serialize())

    def on_peer_handshake(self, message: HandshakeMessage):

        ext_network = message.ext_network
        ext_mask = message.ext_mask
        prov_network = message.prov_network
        prov_mask = message.prov_mask
        dtr = message.dtr

        log.info("[HANDSHAKE]")
        log.info(f"  ext network: {ip2str(ext_network)}, ext mask: {ip2str(ext_mask)}")
        if (
            self.ntw.global_state == WITHOUT_NETWORK
            and self.ntw.local_state == CONNECTED
        ):
            self.ntw.is_local_root = True
            node_networks, new_mask = get_node_subnets(prov_network, prov_mask)
            new_network = node_networks[self.ntw.orientation]
            self.ntw.node_network = message.prov_network
            self.ntw.node_network_mask = message.prov_mask
            self.ntw.my_network = new_network
            self.ntw.my_network_mask = new_mask
            self.ntw.output.add_route(
                self.ntw.node_network, self.ntw.node_network_mask, "spi"
            )
            log.info(f"adding wlan route {ip2str(ext_network)}  {ip2str(ext_mask)}")
            self.ntw.output.add_route(ext_network, ext_mask, "wlan")
            sibling_message = create_message_from_args(
                SiblingMessageType.PROVISION,
                provider_id=self.ntw.orientation,
                network=prov_network,
                mask=prov_mask,
            )
            self.ntw.output.broadcast_to_siblings(sibling_message.serialize())
            log.info(" > Node has been provisioned -- notifying siblings")
            self.ntw.global_state = WITH_NETWORK
        elif ext_network and ext_mask:
            log.info(
                f" > New route found: {ip2str(ext_network)}/{ext_mask.bit_count()} -> wlan-{self.ntw.orientation}"
            )
            log.info(f"adding wlan route {ip2str(ext_network)}  {ip2str(ext_mask)}")
            self.ntw.output.add_route(ext_network, ext_mask, "wlan")

        update_dtr_message = create_message_from_args(
            PeerMessageType.DTR_UPDATE, dtr=dtr
        )
        self.on_update_DTR(update_dtr_message)

    def on_update_DTR(self, message: DtrUpdateMessage):
        peer_dtr = message.dtr
        if peer_dtr == 0:
            # peer is not connected to the network yet
            return
        dtr = self.ntw.dtr
        if dtr == 0 or peer_dtr + 1 < dtr:
            # i am not connected to the network yet or my dtr is can improve
            self.ntw.dtr = peer_dtr + 1
            sibling_message = create_message_from_args(
                SiblingMessageType.DTR_UPDATE, dtr=peer_dtr + 1
            )
            self.ntw.output.broadcast_to_siblings(sibling_message.serialize())
            self.ntw.output.switch_default_gateway("wlan")
            # I am the Default gateway of the node now
            self.ntw.is_local_root = True

    def on_peer_gtw_req(self, message: GtwReqMessage):
        hag_ips = message.hag_ips

        orientation = {1: "n", 2: "e", 3: "s", 4: "w", 5: "c"}[self.ntw.orientation]
        for network in hag_ips.split():
            addr, mask = network.split("/")

            log.warn(
                f"[HAG] Adding {addr}/{mask} -> {orientation} to global route table"
            )
            self.ntw.node_routing_table.add_route(str2ip(addr), int(mask), orientation)

        if hag_ips:
            sibl_message = create_message_from_args(
                SiblingMessageType.UPDATE_NODE_TABLE, table=self.ntw.node_routing_table
            )
            self.ntw.output.broadcast_to_siblings(sibl_message.serialize())
        sibling_message = create_message_from_args(
            SiblingMessageType.SEND_NEW_GTW_REQUEST, hag_ips=hag_ips
        )
        if self.ntw.dtr == 1:
            # I am root
            self.ntw.output.broadcast_to_siblings(sibling_message.serialize())
            return

        if self.ntw.global_state == ON_GTW_REQ:
            return
        self.ntw.global_state = ON_GTW_REQ
        self.ntw.dtr = 0
        self.ntw.output.broadcast_to_siblings(sibling_message.serialize())

    def on_new_gtw_res(self, message: GtwRespMessage):
        ext_network = message.ext_network
        ext_mask = message.ext_mask
        peer_dtr = message.dtr

        if self.ntw.dtr != 0 and self.ntw.dtr <= peer_dtr:
            log.info("ESTE DTR NO ME CONVIENE")
            return
        log.info("Sali perro")

        self.ntw.global_state = WITH_NETWORK
        self.ntw.output.switch_default_gateway("wlan")
        self.ntw.is_local_root = True
        self.ntw.dtr = peer_dtr + 1
        sibling_message = create_message_from_args(
            SiblingMessageType.NEW_GTW_WINNER,
            network=ext_network,
            mask=ext_mask,
            dtr=peer_dtr,
        )
        self.ntw.output.broadcast_to_siblings(sibling_message.serialize())

    def on_peer_lost(self, message: PeerLostMessage):
        network = message.network
        mask = message.mask

        log.info(f"[PEER LOST] {network=} {mask=}")
        log.info(
            f"[PEER LOST] Clearing routing entries for interface `wlan-{'neswc'[self.ntw.orientation - 1]}`"
        )

        # No longer connected to peer
        self.ntw.my_wlan_ip = None
        self.ntw.local_state = NOT_CONNECTED

        # Wirele parented route (default gateway = wlan), we'll switch
        # the DG to SPI.
        self.ntw.output.switch_default_gateway("spi")

        # Wireless peer is lost --> remove all routes that go through via wlan
        lost_routes = self.ntw.output.remove_routes_for_interface("wlan")

        # Inform siblings about lost routes
        sibling_message = create_message_from_args(
            SiblingMessageType.ROUTE_LOST,
            routes=[[route.ip, route.mask] for route in lost_routes],
        )
        self.ntw.output.broadcast_to_siblings(sibling_message.serialize())

        log.info(self)
        if self.ntw.is_local_root:
            self.ntw.is_local_root = False
            self.ntw.dtr = 0
            self.ntw.global_state = ON_GTW_REQ
            log.info("[PEER LOST] Connection to ROOT node has been lost")
            sibling_message = create_message_from_args(
                SiblingMessageType.SEND_NEW_GTW_REQUEST, hag_ips=""
            )
            self.ntw.output.broadcast_to_siblings(sibling_message.serialize())

    def process_message(self, message_id, payload: dict):
        if message_id == PeerMessageType.HANDSHAKE:
            message = create_message(PeerMessageType.HANDSHAKE, payload)
            self.on_peer_handshake(message)
        elif message_id == PeerMessageType.DTR_UPDATE:
            message = create_message(PeerMessageType.DTR_UPDATE, payload)
            self.on_update_DTR(message)
        elif message_id == PeerMessageType.NEW_GTW_REQUEST:
            message = create_message(PeerMessageType.NEW_GTW_REQUEST, payload)
            self.on_peer_gtw_req(message)
        elif message_id == PeerMessageType.NEW_GTW_RESPONSE:
            message = create_message(PeerMessageType.NEW_GTW_RESPONSE, payload)
            self.on_new_gtw_res(message)
        else:
            log.error(f"Unknown external message ID: {message_id}")

    def process_event(self, event_id, payload: dict):
        if event_id == EVENT_ON_PEER_CONNECTED:
            message = create_message(PeerMessageType.ON_CONNECTED, payload)
            self.on_peer_connected(message)
        elif event_id == EVENT_ON_PEER_LOST:
            message = create_message(PeerMessageType.PEER_LOST, payload)
            self.on_peer_lost(message)
        else:
            log.error(f"Unknown external event ID: {event_id}")
