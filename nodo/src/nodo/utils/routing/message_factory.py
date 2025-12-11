from typing import Any, Optional, Union, List, Type

from nodo.routing.routing_table import RoutingTable
from .peer_messages import (
    PeerMessageType,
    OnConnectedMessage,
    HandshakeMessage,
    DtrUpdateMessage,
    GtwReqMessage,
    GtwRespMessage,
    PeerLostMessage,
)
from .sibling_messages import (
    SiblUpdateNodeTableMessage,
    SiblingMessageType,
    RouteLostMessage,
    ProvisionMessage,
    SiblDtrUpdateMessage,
    SiblGtwReqMessage,
    SiblGtwWinnerMessage,
)

# Define type alias for all message classes
Message = Union[
    OnConnectedMessage,
    HandshakeMessage,
    DtrUpdateMessage,
    GtwReqMessage,
    GtwRespMessage,
    RouteLostMessage,
    ProvisionMessage,
    SiblDtrUpdateMessage,
    SiblGtwReqMessage,
    SiblGtwWinnerMessage,
]

# Map message types to their respective classes
MESSAGE_TYPE_MAP: dict[Union[PeerMessageType, SiblingMessageType], Type[Message]] = {
    PeerMessageType.ON_CONNECTED: OnConnectedMessage,
    PeerMessageType.HANDSHAKE: HandshakeMessage,
    PeerMessageType.DTR_UPDATE: DtrUpdateMessage,
    PeerMessageType.NEW_GTW_REQUEST: GtwReqMessage,
    PeerMessageType.NEW_GTW_RESPONSE: GtwRespMessage,
    PeerMessageType.PEER_LOST: PeerLostMessage,
    SiblingMessageType.ROUTE_LOST: RouteLostMessage,
    SiblingMessageType.PROVISION: ProvisionMessage,
    SiblingMessageType.DTR_UPDATE: SiblDtrUpdateMessage,
    SiblingMessageType.SEND_NEW_GTW_REQUEST: SiblGtwReqMessage,
    SiblingMessageType.NEW_GTW_WINNER: SiblGtwWinnerMessage,
    SiblingMessageType.UPDATE_NODE_TABLE: SiblUpdateNodeTableMessage,
}


# Factory function to create message from dict data
def create_message(
    message_type: Union[PeerMessageType, SiblingMessageType], data: dict
) -> Message:
    message_class = MESSAGE_TYPE_MAP.get(message_type)
    if message_class is None:
        raise ValueError(f"Unknown message type: {message_type}")
    data["id"] = message_type
    return message_class(**data)


# Factory function to create message from individual arguments
def create_message_from_args(
    message_type: Union[PeerMessageType, SiblingMessageType],
    ext_network: Optional[int] = None,
    ext_mask: Optional[int] = None,
    prov_network: Optional[int] = None,
    prov_mask: Optional[int] = None,
    dtr: Optional[int] = None,
    hag_ips: Optional[str] = None,
    routes: Optional[List[int]] = None,
    provider_id: Optional[int] = None,
    network: Optional[int] = None,
    mask: Optional[int] = None,
    table: Optional[RoutingTable] = None,
) -> Message:
    message_class = MESSAGE_TYPE_MAP.get(message_type)
    if not message_class:
        raise ValueError(f"Unknown message type: {message_type}")

    if message_class == HandshakeMessage:
        return message_class(
            id=message_type,
            ext_network=ext_network,
            ext_mask=ext_mask,
            prov_network=prov_network,
            prov_mask=prov_mask,
            dtr=dtr,
        )
    if message_class == OnConnectedMessage:
        return message_class(id=message_type, network=network, mask=mask)
    elif message_class == DtrUpdateMessage:
        return message_class(id=message_type, dtr=dtr)
    elif message_class == GtwReqMessage:
        return message_class(id=message_type, hag_ips=hag_ips)
    elif message_class == GtwRespMessage:
        return message_class(
            id=message_type, ext_network=ext_network, ext_mask=ext_mask, dtr=dtr
        )
    elif message_class == RouteLostMessage:
        return message_class(id=message_type, routes=routes)
    elif message_class == ProvisionMessage:
        return message_class(
            id=message_type, provider_id=provider_id, network=network, mask=mask
        )
    elif message_class == SiblDtrUpdateMessage:
        return message_class(id=message_type, dtr=dtr)
    elif message_class == SiblGtwReqMessage:
        return message_class(id=message_type, hag_ips=hag_ips)
    elif message_class == SiblGtwWinnerMessage:
        return message_class(id=message_type, network=network, mask=mask, dtr=dtr)
    elif message_class == SiblUpdateNodeTableMessage:
        return message_class(id=message_type, table=table.json())
    elif message_class == PeerLostMessage:
        return message_class(id=message_type, network=network, mask=mask)
    else:
        raise ValueError(f"Unsupported message type: {message_type}")
