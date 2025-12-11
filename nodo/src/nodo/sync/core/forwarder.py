from nodo.sync.device_core import DeviceCore

SIBL_MSG_REQUEST_TOKEN = "request-token"
SIBL_MSG_TOKEN_GRANT = "token-grant"

IDS_TABLE = {"n": 1, "e": 2, "s": 3, "w": 4, "c": 5}


class ForwarderCore(DeviceCore):
    def __init__(self, orientation):
        super().__init__(f"fwd-{orientation}")
        self.orientation = IDS_TABLE[orientation]
        self.requested_cs = False

    def request_critical_section(self):
        self.requested_cs = True
        self.output.broadcast_to_siblings({"id": SIBL_MSG_REQUEST_TOKEN})

    def on_sibling_message(self, message: dict):
        if message["id"] == SIBL_MSG_TOKEN_GRANT:
            if message["destination"] == self.orientation:
                # We are inside the critical section, clear our flag and notify device
                if self.requested_cs:
                    self.requested_cs = False
                    self.output.on_critical_section()

                # Device has completed processing from critical section, release token
                self._exit_critical_section()

        # Return true if the message is ours
        return message["id"] in (SIBL_MSG_TOKEN_GRANT, SIBL_MSG_REQUEST_TOKEN)

    def _exit_critical_section(self):
        self.output.broadcast_to_siblings(
            {"id": SIBL_MSG_TOKEN_GRANT, "destination": self.orientation + 1}
        )
