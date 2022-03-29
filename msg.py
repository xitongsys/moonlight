from coding import Coding, EC

class MsgType:
    LOGIN = 0
    LOGOUT = 1
    OPEN_CONN = 2
    CLOSE_CONN = 3
    DATA = 4

class MsgLogin:
    def __init__(self, user: str = "", password: str = "", port: int = 0):
        self.type = MsgType.LOGIN
        self.user = user
        self.password = password
        self.port = port

    def encode(self) -> bytearray:
        res = bytearray()
        res += Coding.encode_int(self.type, 1)
        res += Coding.encode_string(self.user)
        res += Coding.encode_string(self.password)
        res += Coding.encode_int(self.port, 2)
        return res

    def decode(self, buf: bytearray) -> int:
        pos = 0
        self.type, size, ec = Coding.decode_int(buf[pos:], 1)
        if ec != EC.NONE:
            return ec
        pos += size

        self.user, size, ec = Coding.decode_string(buf[pos:])
        if ec != EC.NONE:
            return ec
        pos += size

        self.password, size, ec = Coding.decode_string(buf[pos:])
        if ec != EC.NONE:
            return ec
        pos += size

        self.port, size, ec = Coding.decode_int(buf[pos:], 2)
        if ec != EC.NONE:
            return ec

        return 0

class MsgLogout:
    def __init__(self):
        self.type = MsgType.LOGOUT

    def encode(self):
        res = bytearray()
        res += Coding.encode_int(self.type, 1)
        return res
    
    def decode(self, buf):
        self.type, _, ec = Coding.decode_int(buf)
        return ec


class MsgOpenConn:
    def __init__(self):
        self.type = MsgType.OPEN_CONN
        self.uuid = ''

    def encode(self):
        res = bytearray()
        res += Coding.encode_int(self.type, 1)
        res += Coding.encode_string(self.uuid)
        return res
    
    def decode(self, buf):
        pos = 0
        self.type, size, ec = Coding.decode_int(buf[pos:])
        if ec != EC.NONE:
            return ec
        pos += size

        self.uuid, size, ec = Coding.decode_string(buf[pos:])
        return ec


class MsgCloseConn:
    def __init__(self):
        self.type = MsgType.CLOSE_CONN
        self.uuid = ''

    def encode(self):
        res = bytearray()
        res += Coding.encode_int(self.type, 1)
        res += Coding.encode_string(self.uuid)
        return res
    
    def decode(self, buf):
        pos = 0
        self.type, size, ec = Coding.decode_int(buf[pos:])
        if ec != EC.NONE:
            return ec
        pos += size

        self.uuid, size, ec = Coding.decode_string(buf[pos:])
        return ec


class MsgData:
    def __init__(self):
        self.type = MsgType.DATA
        self.uuid = ''
        self.data = b''

    def encode(self):
        res = bytearray()
        res += Coding.encode_int(self.type, 1)
        res += Coding.encode_string(self.uuid)
        res += Coding.encode_bytes(self.data)
        return res
    
    def decode(self, buf):
        pos = 0
        self.type, size, ec = Coding.decode_int(buf[pos:])
        if ec != EC.NONE:
            return ec
        pos += size

        self.uuid, size, ec = Coding.decode_string(buf[pos:])
        if ec != EC.NONE:
            return ec
        pos += size

        self.data, size, ec = Coding.decode_bytes(buf[pos:])
        return ec