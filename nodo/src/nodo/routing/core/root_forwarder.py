from nodo.routing.core.forwarder import ForwarderCore
from nodo.routing.routing_utils import get_node_subnets
from nodo.utils.routing.events import *

# Import enums and classes for types and data structures
from nodo.utils.routing.external_forwarder import ExternalFordwarder
from nodo.utils.routing.internal_forwarder import IternalFordwarder
from nodo.utils.routing.network import Network
from nodo.utils.routing.peer_messages import (
    PeerMessageType,
)
from nodo.utils.routing.sibling_messages import (
    SiblingMessageType,
)
from nodo.routing.device_core import DeviceCore
from pysim_sdk.utils.ip_address import ip2str
from pysim_sdk.utils import log

IDS_TABLE = {"n": 1, "e": 2, "s": 3, "w": 4, "c": 5}


class RootForwarderCore(ForwarderCore):
    def __str__(self):
        return (
            "-------- DEVICE STATUS -- ROOT FORWARDER CORE --------\n"
            + f"  orientation = {self.network.orientation}\n"
            + f"  my_wlan_ip = {self.network.my_wlan_ip}\n"
            + f"  is_local_root = {self.network.is_local_root}\n"
            + f"  node_network = {self.network.node_network and ip2str(self.network.node_network)}\n"
            + f"  node_network_mask = {self.network.node_network_mask and ip2str(self.network.node_network_mask)}\n"
            + f"  my_network = {self.network.my_network and ip2str(self.network.my_network)}\n"
            + f"  my_network_mask = {self.network.my_network_mask and ip2str(self.network.my_network_mask)}\n"
            + f"  my_dtr = {self.network.dtr}\n"
            + "-----------------------------------------------------"
        )
