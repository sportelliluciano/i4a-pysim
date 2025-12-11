from dataclasses import asdict, dataclass
from enum import Enum, auto


# Define PeerMessageType Enum
class PeerMessageType(Enum):
    ON_CONNECTED = "ON_CONNECTED"
    HANDSHAKE = "HANDSHAKE"
    DTR_UPDATE = "DTR_UPDATE"
    NEW_GTW_REQUEST = "NEW_GTW_REQUEST"
    NEW_GTW_RESPONSE = "NEW_GTW_RESPONSE"
    PEER_LOST = "PEER_LOST"


# Define Peer Message Classes


@dataclass
class OnConnectedMessage:
    id: PeerMessageType
    network: int
    mask: int

    def serialize(self) -> dict:
        return asdict(self)


@dataclass
class HandshakeMessage:
    id: PeerMessageType
    ext_network: int
    ext_mask: int
    prov_network: int
    prov_mask: int
    dtr: int

    def serialize(self) -> dict:
        tmp = asdict(self)
        tmp["id"] = tmp["id"].value
        return tmp


@dataclass
class DtrUpdateMessage:
    id: PeerMessageType
    dtr: int

    def serialize(self) -> dict:
        tmp = asdict(self)
        tmp["id"] = tmp["id"].value
        return tmp


@dataclass
class GtwReqMessage:
    id: PeerMessageType
    hag_ips: str

    def serialize(self) -> dict:
        tmp = asdict(self)
        tmp["id"] = tmp["id"].value
        return tmp


@dataclass
class GtwRespMessage:
    id: PeerMessageType
    ext_network: int
    ext_mask: int
    dtr: int

    def serialize(self) -> dict:
        tmp = asdict(self)
        tmp["id"] = tmp["id"].value
        return tmp


@dataclass
class PeerLostMessage:
    id: PeerMessageType
    network: int
    mask: int

    def serialize(self) -> dict:
        tmp = asdict(self)
        tmp["id"] = tmp["id"].value
        return tmp
