from typing import Tuple
from msg import *


def push(buf: bytearray, data: bytes) -> int:
    buf += data
    return len(data)


def pop(buf: bytearray, size: int) -> bytearray:
    size = min(len(bytearray), size)
    res = buf[:size]
    del buf[:size]
    return res


def push_msg(buf: bytearray, type: int, id: str, data: bytes = b'') -> int:
    msg = Msg(type, id, data).encode()
    buf += msg
    return len(msg)


def pop_msg(buf: bytearray) -> Tuple[Msg, int]:
        msg = Msg()
        size, ec = msg.decode(buf)
        if ec == 0 and size > 0:
            del buf[:size]
        return msg, ec
