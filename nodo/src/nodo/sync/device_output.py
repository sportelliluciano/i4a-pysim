class DeviceOutput:
    def on_critical_section(self):
        raise NotImplementedError

    def broadcast_to_siblings(self, message: bytes) -> bool:
        raise NotImplementedError
