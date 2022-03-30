from socket import *
from select import *
from typing import Tuple
from msg import *
from datetime import datetime
import logger
import util
from com import Connection


class Server:
    def __init__(self, addr: str, port: int, max_num: int):
        self.addr, self.port, self.max_num = addr, port, max_num
        self.socket = socket(family=AF_INET, type=SOCK_STREAM, proto=0)
        self.socket.bind((self.addr, self.port))
        self.socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, True)
        self.socket.setblocking(False)
        self.socket.listen(self.max_num)

        logger.info("server start listen {}:{} by max_num = ".format(
            self.addr, self.port, self.max_num))

        self.rsockets, self.wsockets, self.xsockets = [self.socket], [], []

        self.input_buf = bytearray()

        self.ids = {}
        self.conns = {}

    def open_conn(self, conn: socket, addr: str):
        id = "{}-{}".format(self.port, addr)
        connection = Connection(id, conn)
        conn.setblocking(False)
        self.conns[id] = connection
        self.ids[conn] = id
        self.rsockets.append(conn)
        self.wsockets.append(conn)
        util.push_msg(self.input_buf, MsgType.OPEN_CONN, id)

    def close_conn(self, conn):
        if conn in self.ids:
            id = self.conns[conn]
            del self.conns[id]
            del self.ids[conn]

        if conn in self.rsockets:
            self.rsockets.remove(conn)
        if conn in self.wsockets:
            self.wsockets.remove(conn)
        conn.close()

    def push_msg(self, msg: Msg) -> int:
        if msg.id not in self.conns:
            return -1
        util.push(self.conns[msg.id].output_buf, msg.data)

    def pop_msg(self) -> Tuple[Msg, int]:
        return util.pop_msg(self.input_buf)

    def poll(self):
        rsockets, wsockets, xsockets = select(self.rsockets, self.wsockets, self.xsockets, 0)
        for rsocket in rsockets:
            if rsocket is self.socket:
                conn, addr = rsocket.accept()
                self.open_conn(conn, addr)

            else:
                data = rsocket.recv(1024 * 10)
                id = self.ids[rsocket]
                if len(data) > 0:
                    util.push_msg(self.input_buf, MsgType.DATA, id, data)
                else:
                    self.close_conn(rsocket)

        for wsocket in wsockets:
            id = self.ids[wsocket]
            connection = self.conns[id]
            if len(connection.output_buf) == 0:
                continue
            size = wsocket.send(connection.output_buf)
            if size > 0:
                util.pop(connection.output_buf, size)

        for xsocket in xsockets:
            self.close_conn(xsocket)


if __name__ == '__main__':
    server = Server("0.0.0.0", 9001, 1024)
    while True:
        server.poll()
