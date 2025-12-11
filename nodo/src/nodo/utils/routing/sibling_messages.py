from dataclasses import asdict, dataclass
from enum import Enum, auto
from typing import Optional, List


# Define SiblingMessageType Enum
class SiblingMessageType(Enum):
    ROUTE_LOST = "ROUTE_LOST"
    PROVISION = "PROVISION"
    DTR_UPDATE = "DTR_UPDATE"
    SEND_NEW_GTW_REQUEST = "SEND_NEW_GTW_REQUEST"
    NEW_GTW_WINNER = "NEW_GTW_WINNER"
    UPDATE_NODE_TABLE = "UPDATE_NODE_TABLE"


# Define Sibling Message Classes
@dataclass
class RouteLostMessage:
    id: SiblingMessageType
    routes: List[int]

    def serialize(self) -> dict:
        tmp = asdict(self)
        tmp["id"] = tmp["id"].value
        return tmp


@dataclass
class ProvisionMessage:
    id: SiblingMessageType
    provider_id: int
    network: int
    mask: int

    def serialize(self) -> dict:
        tmp = asdict(self)
        tmp["id"] = tmp["id"].value
        return tmp


@dataclass
class SiblDtrUpdateMessage:
    id: SiblingMessageType
    dtr: int

    def serialize(self) -> dict:
        tmp = asdict(self)
        tmp["id"] = tmp["id"].value
        return tmp


@dataclass
class SiblGtwReqMessage:
    id: SiblingMessageType
    hag_ips: str

    def serialize(self) -> dict:
        tmp = asdict(self)
        tmp["id"] = tmp["id"].value
        return tmp


@dataclass
class SiblGtwWinnerMessage:
    id: SiblingMessageType
    network: int
    mask: int
    dtr: int

    def serialize(self) -> dict:
        tmp = asdict(self)
        tmp["id"] = tmp["id"].value
        return tmp


@dataclass
class SiblUpdateNodeTableMessage:
    id: SiblingMessageType
    table: list

    def serialize(self):
        tmp = asdict(self)
        tmp["id"] = tmp["id"].value
        return tmp
