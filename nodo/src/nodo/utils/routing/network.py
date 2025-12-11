from dataclasses import dataclass

from nodo.routing.routing_table import RoutingTable

IDS_TABLE = {"n": 1, "e": 2, "s": 3, "w": 4, "c": 5}

# Local States

NOT_CONNECTED = 0
CONNECTED = 1

# Global States
WITH_NETWORK = 1
WITHOUT_NETWORK = 2
READY = 3
ON_GTW_REQ = 4


@dataclass
class Network:
    def __init__(self, orientation, output_ntw) -> None:
        self.orientation = IDS_TABLE[orientation]
        self.output = output_ntw

        self.node_network = None
        self.node_network_mask = None
        self.my_network = None
        self.my_network_mask = None

        self.is_local_root = False
        self.my_wlan_ip = None

        # Mati time
        self.dtr = 0
        self.local_state = NOT_CONNECTED
        self.global_state = WITHOUT_NETWORK
        self.new_gtw_proposal = []

        self.node_routing_table = RoutingTable("c")
