import socket, select

from . import util
from . import logger
from .msg import Msg, MsgType
from .com import Connection, Rule


class Client:
    BUF_SIZE = 1024 * 256

    def __init__(self, network_name: str = "", saddr: str = "127.0.0.1", sport: int = 9001):
        self.network_name = network_name
        self.saddr, self.sport = saddr, sport
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.saddr, self.sport))
        self.socket.setblocking(False)
        self.rsockets, self.wsockets, self.xsockets = [self.socket], [self.socket], []

        self.input_buf = bytearray()
        self.output_buf = bytearray()

        self.conns = {}
        self.ids = {}

        # send register msg
        util.push_msg(self.output_buf, MsgType.REG, network_name)

    def open_conn(self, id: str, addr: str, port: int):
        logger.debug("[CLIENT] open conn {}".format(id))

        conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        conn.connect((addr, port))
        conn.setblocking(False)
        self.rsockets.append(conn)
        self.wsockets.append(conn)
        self.conns[id] = Connection(id, conn)
        self.ids[conn] = id

    def close_conn(self, id: str):
        logger.debug("[CLIENT] close conn {}".format(id))

        if id in self.conns:
            conn = self.conns[id].conn
            del self.ids[conn]
            del self.conns[id]

    def stop(self):
        self.socket.close()
        exit(-1)

    def start(self):
        while True:
            rsockets, wsockets, xsockets = select.select(self.rsockets, self.wsockets, self.xsockets, 1)

            # read
            for rsocket in rsockets:
                if self.socket is rsocket:
                    data = self.socket.recv(Client.BUF_SIZE)
                    if len(data) == 0:
                        self.stop()
                        return
                    util.push(self.input_buf, data)

                    while True:
                        msg, ec = util.pop_msg(self.input_buf)
                        if ec == 0:
                            logger.debug(
                                "[CLIENT] pop msg type={} id={} len={}".format(msg.type, msg.id, len(msg.data)))

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
                        else:
                            break

                elif rsocket in self.ids:
                    id = self.ids[rsocket]
                    try:
                        data = rsocket.recv(Client.BUF_SIZE)
                        if len(data) > 0:
                            logger.debug("[CLIENT] recv {}".format(len(data)))

                            util.push_msg(self.output_buf, MsgType.DATA, id, data)

                            if self.socket not in self.wsockets:
                                self.wsockets.append(self.socket)

                        else:
                            raise ValueError("conn error")

                    except BlockingIOError:
                        pass
                    except:
                        self.close_conn(id)

                else:
                    if rsocket in self.rsockets:
                        self.rsockets.remove(rsocket)

            # write
            for wsocket in wsockets:
                if wsocket is self.socket and len(self.output_buf) > 0:
                    try:
                        size = wsocket.send(self.output_buf)
                        if size > 0:
                            logger.debug("[CLIENT] send to server {}".format(size))
                            util.pop(self.output_buf, size)

                        if len(self.output_buf) == 0:
                            self.wsockets.remove(self.socket)

                    except BlockingIOError:
                        pass

                    except:
                        self.stop()

                elif wsocket in self.ids:
                    id = self.ids[wsocket]
                    connection = self.conns[id]

                    try:
                        if len(connection.input_buf) > 0:
                            size = wsocket.send(connection.input_buf)

                            logger.debug("[CLIENT] send {}".format(size))

                            if size > 0:
                                util.pop(connection.input_buf, size)

                        if len(connection.input_buf) == 0:
                            self.wsockets.remove(wsocket)

                    except BlockingIOError:
                        pass
                    except:
                        self.close_conn(id)

            # exception
            for xsocket in xsockets:
                if xsocket is self.socket:
                    self.stop()
                    return

                if xsocket in self.ids:
                    id = self.ids[xsocket]
                    self.close_conn(id)


if __name__ == '__main__':
    client = Client()
    client.start()
