import time

import pysim_sdk


class PysimClient(pysim_sdk.PysimClient):
    def __init__(self, orientation, node_id=None, base_url="http://localhost:8080"):
        device_id = {
            "n": "north",
            "e": "east",
            "s": "south",
            "w": "west",
            "c": "center",
        }[orientation]

        super().__init__(device_id, node_id, base_url)

        self._in_critical_section = False
        self._last_cs_request = None
        self._last_cs_enter = None

    def enter_critical_section(self):
        if self._last_cs_request:
            self.event(
                "enter_critical_section",
                time_to_enter_cs=f"{(time.time_ns() - self._last_cs_request)/1e6:.1f} ms",
            )
        else:
            self.event("enter_critical_section")

        self._in_critical_section = True
        self._last_cs_enter = time.time_ns()

    def request_critical_section(self):
        if not self._last_cs_request:
            self._last_cs_request = time.time_ns()
        self.event("request_critical_section")

    def event(self, name, **kwargs):
        super().event(name, cs=self._in_critical_section, **kwargs)

    def exit_critical_section(self):
        self._in_critical_section = False
        self.event(
            "exit_critical_section",
            time_in_cs=f"{(time.time_ns() - self._last_cs_enter)/1e6:.1f} ms",
        )
        self._last_cs_request = None
