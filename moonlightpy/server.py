import yaml, json, random
import socket, select

from . import logger
from . import util
from .com import Connection, Rule
from .msg import Msg, MsgType


class Config:
    def __init__(self, config_file: str = None):
        self.addr = "0.0.0.0"
        self.port = 9001
        self.rules = []

        if config_file:
            with open(config_file) as fp:
                cfg = yaml.safe_load(fp)
                self.addr = cfg['addr']
                self.port = cfg['port']
                self.rules = cfg['rules']


class Server:
    BUF_SIZE = 1024 * 256
    MAX_NUM = 1024 * 4

    def __init__(self, config_file: str = None):
        self.config = Config(config_file)
        self.rules = {}

        self.socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM, proto=0)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        self.socket.setblocking(False)

        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 1)
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 3)
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 5)

        self.socket.bind((self.config.addr, self.config.port))
        self.socket.listen(Server.MAX_NUM)

        self.outter_sockets = {}

        self.network_name_to_inner_id = {}

        self.inner_conns = {}
        self.inner_ids = {}

        self.outter_conns = {}
        self.outter_ids = {}

        self.outter_id_to_inner_id = {}

        self.rsockets, self.wsockets, self.xsockets = [self.socket], [], []

        for line in self.config.rules:
            self.add_rule(line)

        logger.info("[SERVER] start {}".format(json.dumps(self.config.__dict__)))

    def choose_inner_conn(self, network_name: str = ''):
        if network_name == '' or network_name not in self.network_name_to_inner_id:
            cs = list(self.inner_conns.keys())
        else:
            cs = self.network_name_to_inner_id[network_name]

        if len(cs) == 0:
            return None
        return random.choice(cs)

    def create_outter_socket(self, rule: Rule):
        if rule not in self.rules:
            try:
                sk = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM, proto=0)
                sk.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
                sk.setblocking(False)
                sk.bind((rule.to_addr, rule.to_port))
                sk.listen(Server.MAX_NUM)
                self.outter_sockets[sk] = rule
                self.rsockets.append(sk)
                logger.info("[SERVER] create rule {}".format(rule))
            except:
                logger.error("[SERVER] create rule failed {}".format(rule))

    def open_inner_conn(self, inner_id: str, conn: socket):
        if inner_id not in self.inner_conns:
            self.inner_conns[inner_id] = Connection(inner_id, conn)
            self.inner_ids[conn] = inner_id
            conn.setblocking(False)
            self.rsockets.append(conn)
            self.wsockets.append(conn)
            logger.debug("[SERVER] open inner conn {}".format(inner_id))

    def close_inner_conn(self, inner_id: str):
        if inner_id in self.inner_conns:
            connection = self.inner_conns[inner_id]
            for o_id, i_id in list(self.outter_id_to_inner_id.items()):
                if i_id == inner_id:
                    del self.outter_id_to_inner_id[o_id]

            del self.inner_conns[inner_id]
            del self.inner_ids[connection.conn]
            logger.debug("[SERVER] close inner conn {}".format(inner_id))

    def open_outter_conn(self, network_name: str, outter_id: str, conn: socket):
        if outter_id not in self.outter_conns:
            inner_id = self.choose_inner_conn(network_name)
            if inner_id is None:
                logger.error("[SERVER] no client for outter conn {}".format(outter_id))
                return

            self.outter_conns[outter_id] = Connection(outter_id, conn)
            self.outter_ids[conn] = outter_id
            conn.setblocking(False)
            self.rsockets.append(conn)
            self.wsockets.append(conn)
            self.outter_id_to_inner_id[outter_id] = inner_id
            logger.debug("[SERVER] open outter conn {}".format(outter_id))

    def close_outter_conn(self, outter_id: str):
        if outter_id in self.outter_conns:
            connection = self.outter_conns[outter_id]
            if outter_id in self.outter_id_to_inner_id:
                del self.outter_id_to_inner_id[outter_id]

            del self.outter_conns[outter_id]
            del self.outter_ids[connection.conn]
            logger.debug("[SERVER] close outter conn {}".format(outter_id))

    def add_rule(self, line: str):
        line = line.strip()
        rule = Rule()
        if rule.parse_string(line) == 0:
            self.create_outter_socket(rule)

    def read_handler(self, rsockets: list):
        for rsocket in rsockets:
            if rsocket is self.socket:
                conn, addr = rsocket.accept()
                inner_id = "{},{}".format(addr[0], addr[1])
                self.open_inner_conn(inner_id, conn)

            elif rsocket in self.outter_sockets:
                rule = self.outter_sockets[rsocket]

                conn, addr = rsocket.accept()
                outter_id = "{},{},{},{},{}".format(rule.network_name, rule.from_addr, rule.from_port, addr[0], addr[1])
                self.open_outter_conn(rule.network_name, outter_id, conn)

                if outter_id in self.outter_id_to_inner_id:
                    inner_id = self.outter_id_to_inner_id[outter_id]
                    if inner_id in self.inner_conns:
                        inner_conn = self.inner_conns[inner_id]
                        msg = Msg(MsgType.OPEN_CONN, outter_id, )
                        util.push_msg(inner_conn.input_buf, MsgType.OPEN_CONN, outter_id, bytes(rule.__str__(), "utf-8"))

                        if inner_conn.conn not in self.wsockets:
                            self.wsockets.append(inner_conn.conn)
                    else:
                        del self.outter_id_to_inner_id[outter_id]

            elif rsocket in self.inner_ids:
                inner_id = self.inner_ids[rsocket]
                inner_conn = self.inner_conns[inner_id]

                try:
                    data = rsocket.recv(Server.BUF_SIZE)

                    logger.debug("[SERVER] recv from inner {}".format(len(data)))

                    if len(data) > 0:
                        util.push(inner_conn.output_buf, data)
                        while True:
                            msg, ec = util.pop_msg(inner_conn.output_buf)
                            if ec != 0:
                                break

                            # register msg
                            if msg.type == MsgType.REG:
                                network_name = msg.id
                                if network_name not in self.network_name_to_inner_id:
                                    self.network_name_to_inner_id[network_name] = []
                                self.network_name_to_inner_id[network_name].append(inner_id)

                                logger.info("[SERVER] inner REG msg: network_name={}, inner_id={}".format(network_name, inner_id))
                                continue

                            if ec == 0 and msg.id in self.outter_conns:
                                outter_conn = self.outter_conns[msg.id]
                                util.push(outter_conn.output_buf, msg.data)

                                if outter_conn.conn not in self.wsockets:
                                    self.wsockets.append(outter_conn.conn)

                    else:
                        raise ValueError("inner connection error")

                except BlockingIOError:
                    pass
                except:
                    self.close_inner_conn(inner_id)

            elif rsocket in self.outter_ids:
                outter_id = self.outter_ids[rsocket]
                try:
                    data = rsocket.recv(Server.BUF_SIZE)
                    if len(data) > 0:
                        if outter_id not in self.outter_id_to_inner_id:
                            raise ValueError("can't find inner id")

                        inner_id = self.outter_id_to_inner_id[outter_id]
                        inner_conn = self.inner_conns[inner_id]
                        util.push_msg(inner_conn.input_buf, MsgType.DATA, outter_id, data)

                        if inner_conn.conn not in self.wsockets:
                            self.wsockets.append(inner_conn.conn)

                    else:
                        raise ValueError("outter connection error")

                except BlockingIOError:
                    pass
                except:
                    self.close_outter_conn(outter_id)

            else:
                if rsocket in self.rsockets:
                    self.rsockets.remove(rsocket)

    def write_handler(self, wsockets: list):
        for wsocket in wsockets:
            if wsocket in self.inner_ids:
                inner_id = self.inner_ids[wsocket]
                inner_conn = self.inner_conns[inner_id]
                try:
                    size = inner_conn.conn.send(inner_conn.input_buf)

                    logger.debug("[SERVER] send to inner {}".format(size))

                    util.pop(inner_conn.input_buf, size)

                    if len(inner_conn.input_buf) == 0 and inner_conn.conn in self.wsockets:
                        self.wsockets.remove(inner_conn.conn)

                except BlockingIOError:
                    pass
                except:
                    self.close_inner_conn(inner_id)

            elif wsocket in self.outter_ids:
                outter_id = self.outter_ids[wsocket]
                outter_conn = self.outter_conns[outter_id]
                try:
                    size = outter_conn.conn.send(outter_conn.output_buf)

                    logger.debug("[SERVER] send to outter {}".format(size))

                    util.pop(outter_conn.output_buf, size)

                    if len(outter_conn.output_buf) == 0 and outter_conn.conn in self.wsockets:
                        self.wsockets.remove(outter_conn.conn)

                except BlockingIOError:
                    pass
                except:
                    self.close_outter_conn(outter_id)

    def exception_handler(self, xsockets: list):
        for xsocket in xsockets:
            if xsocket in self.outter_ids:
                outter_id = self.outter_ids[xsocket]
                self.close_outter_conn(outter_id)
            elif xsocket in self.inner_ids:
                inner_id = self.inner_ids[xsocket]
                self.close_inner_conn(inner_id)

            if xsocket in self.rsockets:
                self.rsockets.remove(xsocket)
            if xsocket in self.wsockets:
                self.wsockets.remove(xsocket)

    def start(self):
        while True:
            rsockets, wsockets, xsockets = select.select(self.rsockets, self.wsockets, self.xsockets, 1)
            self.read_handler(rsockets)
            self.write_handler(wsockets)
            self.exception_handler(xsockets)


if __name__ == '__main__':
    ms = Server('config.json')
    ms.start()
