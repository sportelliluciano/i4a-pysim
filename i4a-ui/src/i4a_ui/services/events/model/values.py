import base64


def ip2str(ip: int):
    return f"{(ip >> 24) & 0xFF}.{(ip >> 16) & 0xFF}.{(ip >> 8) & 0xFF}.{ip & 0xFF}"


class Value:
    def json(self):
        return self.value


class UnknownValue(Value):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return str(self.value)


class IpValue(Value):
    def __init__(self, ip: int):
        self.value = ip

    def __str__(self):
        return ip2str(self.value)


class MaskValue(Value):
    def __init__(self, mask: int):
        self.value = mask

    def __str__(self):
        return f"{self.value.bit_count()}"


class BytesValue(Value):
    def __init__(self, b64_bytes: str):
        self.value = base64.b64decode(b64_bytes)

    def __str__(self):
        result = ""

        for i, byte in enumerate(self.value):
            if i != 0 and i % 4 == 0:
                result += " "
            result += f"{byte:02X} "

        return result

    def json(self):
        return str(self)
