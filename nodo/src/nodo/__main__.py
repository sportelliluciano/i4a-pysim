import os

import multiprocessing
import multiprocessing as mp
import signal

from argparse import ArgumentParser

from pysim_sdk import PysimClient

from pysim_sdk.utils import log
from .routing.core.forwarder import ForwarderCore
from .routing.core.root_forwarder import RootForwarderCore


SPI_HOST_MAP = {
    "n": 1,
    "e": 2,
    "w": 3,
    "s": 4,
    "c": 5,
}


def main():
    parser = ArgumentParser()

    parser.add_argument(
        "-r",
        "--root",
        action="store_true",
        help="Node will act as root node.",
    )

    parser.add_argument(
        "-e", "--qemu", action="store_true", help="Use QEMU for emulation"
    )

    args = parser.parse_args()

    if args.qemu:
        import nodo.qemu_main as emulator
    else:
        import nodo.device_main as emulator

    node_id = None
    if args.root:
        node_id = "root"

    pysim = PysimClient("c", node_id=node_id)
    if not pysim.is_pysim_ready():
        raise Exception("Could not contact simulation controller")

    config = pysim.get_config()

    wlan_barriers, wlan_unlocks = setup_wlan_barriers(config.get("connect_order", []))
    spi_queues = [mp.Queue() for _ in "newsc"]
    spi_pairs = [
        (spi_queues[i], spi_queues[(i + 1) % len(spi_queues)])
        for i in range(len(spi_queues))
    ]
    fwd_process = [
        mp.Process(
            target=emulator.forwarder_main,
            args=(
                RootForwarderCore if args.root else ForwarderCore,
                node_id,
                orientation,
                in_queue,
                out_queue,
                wlan_barriers,
                wlan_unlocks,
            ),
            name=f"fwd-{orientation}",
        )
        for orientation, (in_queue, out_queue) in zip("news", spi_pairs[:-1])
    ]

    for proc in fwd_process:
        proc.start()

    if args.root:
        multiprocessing.current_process().name = "root"
        emulator.root_main(*spi_pairs[-1])
    else:
        multiprocessing.current_process().name = "home"
        emulator.home_main(*spi_pairs[-1])

    for proc in fwd_process:
        os.kill(proc.pid, signal.SIGINT)
        log.info(f"Waiting for process {proc.name!r} to finish...")
        proc.join()


def setup_wlan_barriers(connect_order):
    # Create inter-process barriers for WLAN interfaces in forwarders
    # This is used to force connection order
    # E.g.: If connection order is n -> e -> s, then
    # - `n` will start unlocked
    # - `e` will start locked and will be unlocked by `n`
    # - `s` will start locked and will be unlocked by `s`
    # - `w` is not affected at all, will start unlocked and won't unlock anyone
    wlan_barriers = {o: mp.Event() for o in "news"}
    for barrier in wlan_barriers.values():
        # By default all barriers are unlocked
        barrier.set()

    wlan_unlocks = {
        o: get_wlan_barrier_to_unlock(o, wlan_barriers, connect_order) for o in "news"
    }
    return wlan_barriers, wlan_unlocks


def get_wlan_barrier_to_unlock(orientation, wlan_barriers, connect_order):
    """
    Returns the WLAN barrier that the forwarder at `orientation` should unlock
    upon the first peer connection.
    """
    if not wlan_barriers or not connect_order:
        return None

    # If connection order is n -> e -> s, then
    # - `n` will start unlocked
    # - `e` will start locked and will be unlocked by `n`
    # - `s` will start locked and will be unlocked by `s`
    # - `w` is not affected at all, will start unlocked and won't unlock anyone

    if orientation not in connect_order:
        # Not part of the order, starts unlocked, unlocks nothing
        return None

    my_barrier = connect_order.index(orientation)
    next_barrier = my_barrier + 1
    if next_barrier >= len(connect_order):  # Last one in the order, unlocks nothing
        return None

    wlan_barrier = wlan_barriers[connect_order[next_barrier]]
    wlan_barrier.clear()  # Lock it
    return wlan_barrier


main()
