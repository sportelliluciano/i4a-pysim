import dataclasses

from i4a_ui.services.events.model.formatter import pretty_print

from .values import *

VALUE_PARSERS = {
    "network": IpValue,
    "ip": IpValue,
    "mask": MaskValue,
    "message": BytesValue,
    "ext_network": IpValue,
    "ext_mask": MaskValue,
}


def parse_values(data):
    parsed = {}

    for attribute, value in data.items():
        value_parser = VALUE_PARSERS.get(attribute, UnknownValue)
        parsed[attribute] = value_parser(value)

    return parsed



@dataclasses.dataclass
class Event:
    timestamp: int
    source: str
    stream: str
    data: dict

    def __init__(self, timestamp: int, source: str, stream: str, data: dict):
        self.timestamp = timestamp
        self.source = source
        self.stream = stream
        self.data = parse_values(data)

    def json(self):
        return {
            "formatted": pretty_print(self),
            "source": self.source,
            "timestamp": self.timestamp,
            "data": {
                attribute: value.json() for attribute, value in self.data.items()
            },
        }
        


@dataclasses.dataclass
class Status:
    def __init__(self, data):
        self.data = parse_values(data)
    
    def json(self):
        return {k: v.json() for k, v in self.data.items()}