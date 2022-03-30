from datetime import datetime
from socket import socket


class Connection:
    def __init__(self, id: str, conn: socket):
        self.id = id
        self.conn = conn
        self.create_time = datetime.now()
        self.update_time = datetime.now()
        self.input_buf = bytearray()
        self.output_buf = bytearray()


class Rule:
    def __init__(self, from_addr: str = '', from_port: int = 0, to_addr: str = '', to_port: int = 0):
        self.from_addr = from_addr
        self.from_port = from_port
        self.to_addr = to_addr
        self.to_port = to_port

    def parse_string(self, s) -> int:
        its = s.split(',')
        if len(its) != 4:
            return -1
        self.from_addr = its[0]
        self.from_port = int(its[1])
        self.to_addr = its[2]
        self.to_port = int(its[3])

    def __hash__(self):
        key = "{},{},{},{}".format(self.from_addr, self.from_port, self.to_addr, self.to_port)
        return key.__hash__()

    def __str__(self):
        key = "{},{},{},{}".format(self.from_addr, self.from_port, self.to_addr, self.to_port)
        return key
