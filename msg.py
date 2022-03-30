from coding import Coding, EC


class MsgType:
    OPEN_CONN = 1
    CLOSE_CONN = 2
    DATA = 3

class Msg:
    def __init__(self, type:int = MsgType.DATA, id: str = '', data: bytes = b''):
        self.type = type
        self.id = id
        self.data = data

    def encode(self) -> bytearray:
        res = bytearray()
        res += Coding.encode_int(self.type, 1)
        res += Coding.encode_string(self.id)
        res += Coding.encode_bytes(self.data)
        return res

    def decode(self, buf: bytearray):
        pos = 0
        self.type, size, ec = Coding.decode_int(buf[pos:])
        if ec != EC.NONE:
            return 0, ec
        pos += size

        self.id, size, ec = Coding.decode_string(buf[pos:])
        if ec != EC.NONE:
            return 0, ec
        pos += size

        self.data, size, ec = Coding.decode_bytes(buf[pos:])
        pos += size

        return pos, ec
