EVENT_ON_PEER_CONNECTED = 0
EVENT_ON_PEER_MESSAGE = 1
EVENT_ON_PEER_LOST = 2
EVENT_ON_SIBLING_MESSAGE = 3


class RoutingEvent:
    def __init__(self, event_type, payload=None):
        self.type = event_type
        self.payload = payload
