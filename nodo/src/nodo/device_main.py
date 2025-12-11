from pysim_sdk.nic.internet_tunnel import InternetTunnel
from pysim_sdk.nic.nic_queue import NicQueue
from pysim_sdk.nic.spi import SpiInterface
from pysim_sdk.nic.tun_tunnel import WlanTunnel
from pysim_sdk.nic.wireless.ap import WirelessAp
from pysim_sdk.nic.wireless.station import WirelessStation
from pysim_sdk.utils import log

from nodo.device import Device
from nodo.pysim_client import PysimClient
from nodo.routing.core.home import HomeCore
from nodo.routing.core.root import RootCore
from nodo.sync.core.forwarder import ForwarderCore as SyncForwarderCore
from nodo.sync.core.center import CenterCore as SyncCenterCore


SPI_HOST_MAP = {
    "n": 1,
    "e": 2,
    "w": 3,
    "s": 4,
    "c": 5,
}


def forwarder_main(
    forwarder_class, node_id, orientation, spi_in, spi_out, wlan_barriers, wlan_unlocks
):
    return device_main(
        spi_in,
        spi_out,
        orientation,
        forwarder_class(orientation),
        SyncForwarderCore(orientation),
        node_id=node_id,
        wlan_barriers=wlan_barriers,
        wlan_unlocks=wlan_unlocks,
    )


def home_main(spi_in, spi_out):
    return device_main(
        spi_in, spi_out, "c", HomeCore(), SyncCenterCore(), wlan_ctor=WlanTunnel
    )


def root_main(spi_in, spi_out):
    return device_main(
        spi_in,
        spi_out,
        "c",
        RootCore(),
        SyncCenterCore(),
        node_id="root",
        wlan_ctor=lambda sink: InternetTunnel(sink, "eth0"),
    )


def device_main(
    spi_in,
    spi_out,
    orientation,
    routing_core,
    sync_core,
    node_id=None,
    wlan_ctor=None,
    wlan_barriers=None,
    wlan_unlocks=None,
):
    with PysimClient(orientation, node_id=node_id) as pysim:
        log.configure(pysim)

        config = pysim.get_config()
        name = config["name"]
        links = config["links"]

        events_queue = NicQueue()
        spi_if = SpiInterface(
            f"spi-{orientation}",
            events_queue,
            spi_in,
            spi_out,
            ip_addr=f"127.0.0.{SPI_HOST_MAP[orientation]}",
            next_hop_ip_addr=f"127.0.0.{(SPI_HOST_MAP[orientation] % 5) + 1}",
        )

        if wlan_ctor:
            wlan_if = wlan_ctor(events_queue)
        else:
            if dst_ap_name := links.get(orientation):
                wlan_if = WirelessStation(
                    f"wlan-{orientation}",
                    events_queue,
                    dst_ap_name,
                    wlan_barriers[orientation],
                    wlan_unlocks[orientation],
                    connect_delay=config["connect_delay"],
                )
            else:
                wlan_if = WirelessAp(
                    f"wlan-{orientation}", events_queue, f"{name}.{orientation}"
                )

        device = Device(
            orientation,
            events_queue,
            spi_if,
            wlan_if,
            routing_core,
            sync_core,
        )

        pysim.watch(device)

        try:
            device.main()
        except KeyboardInterrupt:
            log.info("Graceful quit requested")

        log.info(f"Device {name} finished")
