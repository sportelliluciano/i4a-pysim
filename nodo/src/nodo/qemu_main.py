import struct

from scapy.layers.inet import IP
from scapy.layers.l2 import Ether

from pysim_sdk.qemu.handler import QemuHandler
from pysim_sdk.nic.internet_tunnel import InternetTunnel
from pysim_sdk.nic.spi import SpiInterface
from pysim_sdk.nic.wireless.ap import WirelessAp
from pysim_sdk.nic.wireless.station import WirelessStation
from pysim_sdk.nic.tap_tunnel import WlanL2Tunnel
from pysim_sdk.utils import log
from pysim_sdk.utils.ip_address import str2ip

from nodo.pysim_client import PysimClient

WIFI_MODE_STA = 1
WIFI_MODE_AP = 2
WIFI_MODE_APSTA = 3


SPI_HOST_MAP = {
    "n": 1,
    "e": 2,
    "s": 3,
    "w": 4,
    "c": 5,
}


def forwarder_main(
    _, node_id, orientation, spi_in, spi_out, wlan_barriers, wlan_unlocks
):
    return qemu_main(
        spi_in,
        spi_out,
        orientation,
        node_id=node_id,
        wlan_barriers=wlan_barriers,
        wlan_unlocks=wlan_unlocks,
    )


def home_main(spi_in, spi_out):
    return qemu_main(
        spi_in,
        spi_out,
        "c",
        wlan_ctor=WlanL2Tunnel,
    )


def root_main(spi_in, spi_out):
    return qemu_main(
        spi_in,
        spi_out,
        "c",
        node_id="root",
        wlan_ctor=lambda sink: InternetTunnel(sink, "eth0", layer_2=True, mtu=1440),
    )


class View:
    def __init__(self, spi_if, wlan_if, orientation, events_queue):
        self.spi_if = spi_if
        self.wlan_if = wlan_if
        self.events_queue = events_queue
        self.orientation = orientation

    def status(self):
        return {
            "orientation": self.orientation,
            "events": self.events_queue.status(),
            "interfaces": {
                "spi": self.spi_if.status(),
                "wlan": self.wlan_if.status(),
            },
        }


def qemu_main(
    spi_in,
    spi_out,
    orientation,
    node_id=None,
    wlan_ctor=None,
    wlan_barriers=None,
    wlan_unlocks=None,
):
    if orientation == "c":
        if node_id == "root":
            config_bits = 0b101
        else:
            config_bits = 0b100
    else:
        config_bits = {"n": 0b000, "e": 0b010, "w": 0b011, "s": 0b001}[orientation]

    with PysimClient(orientation, node_id=node_id) as pysim:
        log.configure(pysim)

        qemu = QemuHandler(
            pysim=pysim,
            qemu_path="/usr/bin/qemu-system-xtensa",
            flash_file="/build/qemu_flash.bin",
            efuse_file="/build/qemu_efuse.bin",
        )

        config = pysim.get_config()
        name = config["name"]
        links = config["links"]

        qemu_queue = QemuQueueWrapper(qemu, pysim)

        spi_if = SpiInterface(
            f"spi-{orientation}",
            qemu_queue,
            spi_in,
            spi_out,
            ip_addr=f"127.0.0.{SPI_HOST_MAP[orientation]}",
            next_hop_ip_addr=f"127.0.0.{(SPI_HOST_MAP[orientation] % 5) + 1}",
        )

        wlan_mode = None
        if wlan_ctor:
            wlan_if = wlan_ctor(qemu_queue)
        else:
            if dst_ap_name := links.get(orientation):
                wlan_if = WirelessStation(
                    f"wlan-{orientation}",
                    qemu_queue,
                    dst_ap_name,
                    wlan_barriers[orientation],
                    wlan_unlocks[orientation],
                    connect_delay=config["connect_delay"],
                    start_scanning=False,
                    enabled=False,
                )
                wlan_mode = WIFI_MODE_STA
            else:
                wlan_if = WirelessAp(
                    f"wlan-{orientation}",
                    qemu_queue,
                    f"{name}.{orientation}",
                    enabled=False,
                )
                wlan_mode = WIFI_MODE_AP

        wlan_mode_set = None
        qemu_queue.set_spi_if(spi_if)
        qemu_queue.set_wifi_mode(None)

        @qemu.command(0x01)
        def spi_tx(conn, _, payload):
            pysim.event("spi_send", payload_size=len(payload), data=str(IP(payload)))
            spi_if.send_packet(payload)
            conn.write_response(0)

        @qemu.command(0x03)
        def read_config_bits(conn, _, __):
            pysim.event("config_read", result=config_bits)
            conn.write_response(config_bits)

        @qemu.command(0x05)
        def wifi_set_mode(conn, _, payload):
            nonlocal wlan_mode, wlan_mode_set
            (mode,) = struct.unpack("<I", payload)

            if wlan_mode == WIFI_MODE_AP and mode in (WIFI_MODE_AP, WIFI_MODE_APSTA):
                qemu_queue.set_wifi_mode(WIFI_MODE_AP)
            elif wlan_mode == WIFI_MODE_STA and mode in (
                WIFI_MODE_STA,
                WIFI_MODE_APSTA,
            ):
                qemu_queue.set_wifi_mode(WIFI_MODE_STA)
            elif not wlan_mode:
                qemu_queue.set_wifi_mode(mode)
                wlan_mode_set = mode
            else:
                qemu_queue.set_wifi_mode(None)

            pysim.event("wifi_set_mode", mode=mode)
            conn.write_response(0)

        @qemu.command(0x06)
        def wifi_set_ap_config(conn, _, payload):
            ssid, password, channel = struct.unpack("<32s64sI", payload)
            pysim.event(
                "wifi_set_ap_config",
                ssid=ssid.decode("utf-8"),
                password=password.decode("utf-8"),
                channel=channel,
            )
            conn.write_response(0)

        @qemu.command(0x07)
        def wifi_set_sta_config(conn, _, payload):
            ssid, password = struct.unpack("<32s64s", payload)
            pysim.event("wifi_set_sta_config", ssid=ssid, password=password)
            conn.write_response(0)

        @qemu.command(0x08)
        def wifi_connect(conn, _, __):
            conn.write_response(0)  # or 1
            pysim.event("wifi_connect", result=0)
            wlan_if.start_scanning()

        @qemu.command(0x09)
        def wifi_disconnect(conn, _, __):
            conn.write_response(0)
            pysim.event("wifi_disconnect")

        @qemu.command(0x0A)
        def wifi_deauth_sta(conn, _, payload):
            (sta_index,) = struct.unpack("<H", payload)
            conn.write_response(0)
            pysim.event("wifi_deauth_sta", sta_index=sta_index)

        @qemu.command(0x0B)
        def wifi_start(conn, _, __):
            wlan_if.enable()
            conn.write_response(0)
            pysim.event("wifi_start")
            if wlan_mode == WIFI_MODE_AP or (
                not wlan_mode and wlan_mode_set == WIFI_MODE_AP
            ):
                wlan_if.enable_ap_mode(str2ip("192.168.3.1"), str2ip("255.255.255.0"))
                pysim.event("ENABLE_AP_MODE")

        @qemu.command(0x0C)
        def wifi_stop(conn, _, __):
            wlan_if.disable()
            conn.write_response(0)
            pysim.event("wifi_stop")

        @qemu.command(0x0D)
        def wifi_scan_get_ap_num(conn, _, __):
            if links.get(orientation):
                conn.write_response(1)
                pysim.event("wifi_scan_get_ap_num", result=1)
            else:
                conn.write_response(0)
                pysim.event("wifi_scan_get_ap_num", result=0)

        @qemu.command(0x0F)
        def wifi_scan_get_ap_record(conn, _, __):
            bssid = b"\xaa\xaa\x00\x01\x02\x03"
            ssid = (b"I4A-QEMU" + b"\x00" * 33)[:33]
            primary = b"\x0A"
            rssi = b"\x00"
            conn.write_response(0, bssid + ssid + primary + rssi)
            pysim.event("wifi_scan_get_ap_record")

        @qemu.command(0x10)
        def esp_wifi_scan_start(conn, _, __):
            conn.write_response(0)
            pysim.event("wifi_scan_start")

        @qemu.command(0x11)
        def esp_wifi_sta_get_ap_info(conn, _, __):
            bssid = b"\xaa\xaa\x00\x01\x02\x03"
            ssid = (b"I4A-QEMU" + b"\x00" * 33)[:33]
            primary = b"\x0A"
            rssi = b"\x00"
            conn.write_response(0, bssid + ssid + primary + rssi)
            pysim.event("wifi_sta_get_ap_info")

        @qemu.command(0x12)
        def esp_wifi_ap_get_sta_list_count(conn, _, __):
            conn.write_response(0)
            pysim.event("wifi_ap_get_sta_list_count", response=0)

        @qemu.command(0x13)
        def esp_wifi_ap_get_sta_list_data(conn, _, payload):
            index = struct.unpack("<I", payload)[0]
            mac = b"\x00\x00\x00\x00\x00\x00"
            rssi = b"\x00"
            conn.write_response(0xFF, mac + rssi)
            pysim.event("wifi_ap_get_sta_list_item", index=index, result="not-found")

        @qemu.command(0x14)
        def wifi_sta_tx(conn, _, payload):
            pysim.event("WLAN_ST_SEND", sz=len(payload), data=str(Ether(payload)))
            wlan_if.send_packet(payload)
            conn.write_response(0)

        @qemu.command(0x17)
        def wifi_ap_tx(conn, _, payload):
            pysim.event("WLAN_AP_SEND", sz=len(payload), data=str(Ether(payload)))
            wlan_if.send_packet(payload)
            conn.write_response(0)

        with spi_if, wlan_if:
            qemu.run()


class QemuQueueWrapper:
    def __init__(self, handler: QemuHandler, pysim):
        self.handler = handler
        self.pysim = pysim
        self.spi_if = None
        self.wifi_mode = None

    def set_spi_if(self, spi_if):
        self.spi_if = spi_if

    def set_wifi_mode(self, mode):
        self.wifi_mode = mode

    def put(self, event):
        iface, event_name, payload = event
        if event_name == "packet-received":
            if iface == self.spi_if:
                self.pysim.event(
                    "spi_recv", payload_size=len(payload), data=str(IP(payload))
                )
                self.handler.publish_event(1, payload)

            elif self.wifi_mode == WIFI_MODE_AP:
                self.handler.publish_event(6, payload)
                self.pysim.event(
                    "wifi_ap_recv", sz=len(payload), data=str(Ether(payload))
                )
            elif self.wifi_mode == WIFI_MODE_STA:
                self.handler.publish_event(7, payload)
                self.pysim.event(
                    "wifi_st_recv", sz=len(payload), data=str(Ether(payload))
                )
            else:
                log.error(
                    f"Dropping packet {str(Ether(payload))} -- incorrect wlan mode ({self.wifi_mode})"
                )
        elif event_name == "peer-connected":
            if self.wifi_mode == WIFI_MODE_AP:
                self.handler.publish_event(2)
                self.pysim.event("wifi_sta_arrived")
            elif self.wifi_mode == WIFI_MODE_STA:
                self.handler.publish_event(4)
                self.pysim.event("wifi_connected")
            else:
                log.error(
                    f"Dropping peer-connected -- incorrect wlan mode ({self.wifi_mode})"
                )
        elif event_name == "peer-lost":
            if self.wifi_mode == WIFI_MODE_AP:
                self.handler.publish_event(3)
                self.pysim.event("wifi_sta_gone")
            elif self.wifi_mode == WIFI_MODE_STA:
                self.handler.publish_event(5)
                self.pysim.event("wifi_ap_gone")
            else:
                log.error(
                    f"Dropping peer-lost -- incorrect wlan mode ({self.wifi_mode})"
                )
        else:
            raise RuntimeError(f"Dropping event {event!r}")
