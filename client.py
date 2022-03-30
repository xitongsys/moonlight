from socket import *
from select import *
from msg import *
from com import *
import util


class Client:
    def __init__(self, saddr: str, sport: int):
        self.saddr, self.sport = saddr, sport
        self.socket = socket(AF_INET, SOCK_STREAM)
        self.socket.connect((self.saddr, self.sport))
        self.socket.setblocking(False)
        self.rsockets, self.wsockets, self.xsockets = [self.socket], [self.socket], []

        self.input_buf = bytearray()
        self.ouput_buf = bytearray()

        self.conns = {}
        self.ids = {}

    def open_conn(self, id: str, addr: str, port: int):
        conn = socket(AF_INET, SOCK_STREAM)
        conn.connect((addr, port))
        conn.setblocking(False)
        self.rsockets.append(conn)
        self.wsockets.append(conn)
        self.conns[id] = Connection(id, conn)
        self.ids[conn] = id

    def close_conn(self, id: str):
        if id in self.conns:
            conn = self.conns[id].conn
            del self.conns[id]
            del self.ids[id]

    def stop(self):
        self.socket.close()
        exit(-1)

    def start(self):
        while True:
            rsockets, wsockets, xsockets = select(self.rsockets, self.wsockets, self.xsockets, 10)

            # read
            for rsocket in rsockets:
                if self.socket is rsocket:
                    data = self.socket.recv(1024 * 10)
                    if len(data) == 0:
                        self.stop()
                        continue

                    util.push(self.input_buf, data)
                    msg, ec = util.pop_msg(self.input_buf)
                    if ec == 0:
                        if msg.type == MsgType.OPEN_CONN:
                            rule_str = str(msg.data)
                            rule = Rule()
                            if rule.parse_string(rule_str) == 0:
                                self.open_conn(msg.id, rule.from_addr, rule.from_port)

                        elif msg.id in self.conns:
                            connection = self.conns[msg.id]
                            util.push(connection.input_buf, msg.data)

                else:
                    id = self.ids[rsocket]
                    connection = self.conns[id]
                    data = self.socket.recv(1024 * 10)
                    if len(data) == 0:
                        self.close_conn(id)
                        continue
                    util.push_msg(self.ouput_buf, MsgType.DATA, id, data)

            # write
            for wsocket in wsockets:
                if wsocket is self.socket and len(self.ouput_buf) > 0:
                    size = wsocket.send(self.ouput_buf)
                    if size > 0:
                        util.pop(self.output_buf, size)

                elif wsocket is not self.socket:
                    id = self.ids[wsocket]
                    connection = self.conns[id]
                    size = wsocket.send(connection.input_buf)
                    if size > 0:
                        util.pop(connection.input_buf, size)
