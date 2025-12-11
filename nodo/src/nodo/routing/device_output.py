class DeviceOutput:
    def send_peer_message(self, message: dict):
        raise NotImplementedError

    def broadcast_to_siblings(self, message: dict) -> bool:
        raise NotImplementedError

    def switch_default_gateway(self, iface: str):
        raise NotImplementedError

    def add_route(self, network, mask, iface):
        raise NotImplementedError

    def remove_route(self, network, mask):
        raise NotImplementedError

    def remove_routes_for_interface(self, iface: str):
        raise NotImplementedError

    def enable_ap_mode(self, network, mask):
        raise NotImplementedError

    def scan_wireless_peers(self):
        raise NotImplementedError
