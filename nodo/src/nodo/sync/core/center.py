from nodo.sync.device_core import DeviceCore

SIBL_MSG_REQUEST_TOKEN = "request-token"
SIBL_MSG_TOKEN_GRANT = "token-grant"

CENTER_ORIENTATION_ID = 5

# First device to get the token is the immediate next to the center one,
# so we can ensure that once we got the token back it has reached all
# the other devices.
FIRST_DEVICE_TO_GET_TOKEN = (CENTER_ORIENTATION_ID % 5) + 1


class CenterCore(DeviceCore):
    def __init__(self):
        super().__init__("center")

        self.requested_cs = True
        self.requested_tokens = 0
        self.is_token_out = False

    def request_critical_section(self):
        self.output.event("request_critical_section")
        # Center node eventually gets a critical section from a sibling. It cannot request one.
        self.requested_cs = True

    def on_sibling_message(self, message: dict):
        if message["id"] == SIBL_MSG_REQUEST_TOKEN:
            self._on_request_token()
        elif message["id"] == SIBL_MSG_TOKEN_GRANT:
            self._on_token_grant(message["destination"])

        # Return true if the message is ours
        return message["id"] in (SIBL_MSG_TOKEN_GRANT, SIBL_MSG_REQUEST_TOKEN)

    def _on_request_token(self):
        if self.is_token_out:
            # A token hasn't returned yet, queue a new one
            self.requested_tokens += 1
        else:
            # No tokens in the loop, issue a new one
            self._issue_new_token()

    def _on_token_grant(self, destination):
        if destination != CENTER_ORIENTATION_ID:
            return

        # Token has returned, enter our critical section
        if self.requested_cs:
            self.requested_cs = False
            self.output.on_critical_section()

        # Exit the critical section and send the token back or destroy it if it's no longer needed
        if self.requested_tokens > 0:
            # More tokens have been requested while this one was around, send a new one
            self.requested_tokens -= 1
            self._issue_new_token()
        else:
            # No more tokens needed, destroy the current one
            self.is_token_out = False

    def _issue_new_token(self):
        self.is_token_out = True
        self.output.broadcast_to_siblings(
            {"id": SIBL_MSG_TOKEN_GRANT, "destination": FIRST_DEVICE_TO_GET_TOKEN}
        )
