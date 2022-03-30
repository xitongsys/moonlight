class EC:
    NONE = 0
    NEED_MORE = 1
    ERROR = -1

class Coding:
    def encode_int(v, size):
        res = bytearray()
        for i in range(size):
            res.append((v >> (i*8)) & 0xff)
        return res

    def decode_int(buf, size):
        if len(buf) < size:
            return 0, 0, EC.NEED_MORE

        res = 0
        for i in range(size):
            res |= int(buf[i]) << (i * 8)

        return res, size, EC.NONE

    def encode_string(v):
        res = bytearray()
        n = len(v)
        res += Coding.encode_int(n, 4)
        res += v
        return res

    def decode_string(buf):
        n, ec = Coding.decode_int(buf, 4)
        if ec != EC.NONE:
            return ec
        if len(buf) < n + 4:
            return "", 0, EC.NEED_MORE

        return buf[4:4 + n], 4+n, EC.NONE

    def encode_bytes(v):
        res = bytearray()
        n = len(v)
        res += Coding.encode_int(n, 4)
        res += v
        return res

    def decode_bytes(buf):
        n, ec = Coding.decode_int(buf, 4)
        if ec != EC.NONE:
            return ec
        if len(buf) < n + 4:
            return "", 0, EC.NEED_MORE

        return buf[4:4 + n], 4+n, EC.NONE
