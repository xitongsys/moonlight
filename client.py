from socket import *
from select import *

import logger
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
        self.output_buf = bytearray()

        self.conns = {}
        self.ids = {}

    def open_conn(self, id: str, addr: str, port: int):
        logger.info("[CLIENT] open conn id={}, {}:{}".format(id, addr, port))

        conn = socket(AF_INET, SOCK_STREAM)
        conn.connect((addr, port))
        conn.setblocking(False)
        self.rsockets.append(conn)
        self.wsockets.append(conn)
        self.conns[id] = Connection(id, conn)
        self.ids[conn] = id

    def close_conn(self, id: str):
        logger.info("[CLIENT] close conn {}".format(id))

        if id in self.conns:
            conn = self.conns[id].conn
            del self.ids[conn]
            del self.conns[id]

    def stop(self):
        self.socket.close()
        exit(-1)

    def start(self):
        while True:
            rsockets, wsockets, xsockets = select(self.rsockets, self.wsockets, self.xsockets, 1000)

            # read
            for rsocket in rsockets:
                if self.socket is rsocket:
                    data = self.socket.recv(1024 * 10)
                    if len(data) == 0:
                        self.stop()
                        return

                    util.push(self.input_buf, data)
                    msg, ec = util.pop_msg(self.input_buf)
                    if ec == 0:
                        logger.debug("[CLIENT] pop msg {}".format(msg.__dict__))

                        if msg.type == MsgType.OPEN_CONN:
                            rule_str = msg.data.decode(encoding="utf-8")
                            rule = Rule()
                            if rule.parse_string(rule_str) == 0:
                                self.open_conn(msg.id, rule.from_addr, rule.from_port)

                        elif msg.id in self.conns:
                            connection = self.conns[msg.id]
                            util.push(connection.input_buf, msg.data)

                            if connection.conn not in self.wsockets:
                                self.wsockets.append(connection.conn)

                elif rsocket in self.ids:
                    id = self.ids[rsocket]
                    connection = self.conns[id]

                    try:
                        data = rsocket.recv(1024 * 10)
                        logger.debug("[CLIENT] recv {}".format(len(data)))
                        if len(data) == 0:
                            raise ValueError("close conn")

                        util.push_msg(self.output_buf, MsgType.DATA, id, data)

                        if self.socket not in self.wsockets:
                            self.wsockets.append(self.socket)
                    except:
                        self.close_conn(id)

            # write
            for wsocket in wsockets:
                if wsocket is self.socket and len(self.output_buf) > 0:
                    size = wsocket.send(self.output_buf)
                    if size > 0:
                        logger.debug("[CLIENT] send to mainserver {}".format(size))
                        util.pop(self.output_buf, size)

                    if len(self.output_buf) == 0:
                        self.wsockets.remove(self.socket)

                elif wsocket is not self.socket and wsocket in self.ids:
                    id = self.ids[wsocket]
                    connection = self.conns[id]
                    if len(connection.input_buf) > 0:
                        size = wsocket.send(connection.input_buf)

                        logger.debug("[CLIENT] send {}".format(size))

                        if size > 0:
                            util.pop(connection.input_buf, size)

                    if len(connection.input_buf) == 0:
                        self.wsockets.remove(wsocket)

            for xsocket in xsockets:
                if xsocket is self.socket:
                    self.stop()
                    return

                if xsocket in self.ids:
                    id = self.ids[xsocket]
                    self.close_conn(id)


if __name__ == '__main__':
    #client = Client("139.224.117.52", 9001)
    client = Client("127.0.0.1", 9001)
    client.start()
