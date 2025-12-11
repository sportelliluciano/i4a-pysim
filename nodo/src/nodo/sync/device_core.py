from nodo.sync.device_output import DeviceOutput


class DeviceCore:
    def __init__(self, name):
        self.output = None
        self.name = name

    def register_output(self, output: DeviceOutput):
        self.output = output

    def on_sibling_message(self, message: bytes):
        pass
