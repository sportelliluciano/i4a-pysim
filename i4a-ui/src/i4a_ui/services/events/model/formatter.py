import json


def pretty_print(event):
    if event.stream == "events":
        # formatter = FORMATTERS.get(str(event.data["event"]), default_formatter)
        return default_formatter(event.data)

    if event.stream == "logs":
        return json.loads(event.data["msg"].value).get("event", str(event.data["msg"]))

    if event.stream == "status":
        result = ""
        for attr, val in event.data.items():
            result += f"> {attr}\n{val}\n\n"
        return result

    return None


def default_formatter(event):
    data = {
        k: v
        for k, v in event.items()
        if k not in ("orientation", "event", "timestamp", "cs")
    }

    # Merge network + mask into network/prefix len
    if "network" in data and "mask" in data:
        data["network"] = f"{data['network']}/{data.pop('mask')}"

    if "ext_network" in data and "ext_mask" in data:
        data["ext_network"] = f"{data['ext_network']}/{data.pop('ext_mask')}"

    result = ""
    for key, value in data.items():
        result += f"{key}={value} "

    return result.strip()


def add_route_fmt(event):
    return f"{event['network']}/{event['mask']} -> {event['iface']}"


def switch_default_gw_fmt(event):
    return f"{event['iface']}"


def broadcast_to_siblings_fmt(event):
    msg = event["message"]
    return f"{msg}"


def send_peer_message_fmt(event):
    msg = event["message"]
    return f"{msg}"


def enable_ap_mode_fmt(event):
    return f"{event['network']}/{event['mask']}"


FORMATTERS = {
    "add_route": add_route_fmt,
    "switch_default_gateway": switch_default_gw_fmt,
    "broadcast_to_siblings": broadcast_to_siblings_fmt,
    "enable_ap_mode": enable_ap_mode_fmt,
    "send_peer_message": send_peer_message_fmt,
}
