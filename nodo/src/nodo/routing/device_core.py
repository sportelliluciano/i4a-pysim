from pysim_sdk.utils import log
from nodo.routing.device_output import DeviceOutput
from pysim_sdk.utils.ip_address import ip2str


class DeviceCore:
    def __init__(self, name):
        self.output = None
        self.name = name

    def register_output(self, output: DeviceOutput):
        self.output = output

    def on_start(self):
        pass

    def on_peer_connected(self, network: int, mask: int):
        log.info(
            f"[{self.name}] Ignored message: on_peer_connected(network={ip2str(network)}, mask={ip2str(mask)})"
        )

    def on_peer_message(self, message: dict):
        log.info(f"[{self.name}] Ignored message: on_peer_message({message})")

    def on_peer_lost(self, network: int, mask: int):
        log.info(f"[{self.name}] Ignored message: on_peer_lost({network=}, {mask=})")

    def on_sibling_message(self, message: dict):
        log.info(f"[{self.name}] Ignored message: on_sibling_message({message})")

    def on_critical_section(self):
        pass

    def on_forward(self, src_ip: str, dst_ip: str):
        pass

    def on_tick(self):
        pass

    def status(self):
        pass

    def on_change_default_gateway(self, gw: str):
        pass

    def do_forward(self, ip_dst: str):
        return None
