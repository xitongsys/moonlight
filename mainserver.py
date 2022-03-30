import json
from socket import *
from select import *
import logger
import server
import util
from com import Connection, Rule
from msg import *
import random


class Config:
    def __init__(self, config_file: str = None):
        self.addr = "0.0.0.0"
        self.port = 9001
        self.max_num = 1024
        self.rule_file = ''

        if config_file:
            with open(config_file) as fp:
                cfg = json.load(fp)
                self.addr = cfg['addr']
                self.port = cfg['port']
                self.max_num = cfg['max_num']
                self.rule_file = cfg['rule_file']


class MainServer:
    def __init__(self, config_file: str = None):
        self.config = Config(config_file)
        self.socket = socket(family=AF_INET, type=SOCK_STREAM, proto=0)
        self.socket.bind((self.config.addr, self.config.port))
        self.socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, True)
        self.socket.setblocking(False)
        self.socket.listen(self.config.max_num)

        logger.info("laurel start {}".format(json.dumps(self.config.__dict__)))

        self.id2client, self.id2server = {}, {}

        # rule -> server
        self.rules = {}

        # client_id -> connection
        self.clients = {}
        # conn -> client_id
        self.client_ids = {}

        self.rsockets, self.wsockets, self.xsockets = [self.socket], [], []

    def choose_client(self):
        cs = list(self.clients.values())
        return random.choice(cs)

    def create_server(self, rule: Rule):
        if rule not in self.rules:
            self.rules[rule] = server.Server(rule.to_addr, rule.to_port, self.config.max_num)

    def create_client(self, client_id: str, conn: socket):
        logger.info("[MAINSERVER] create client {}".format(client_id))
        if client_id not in self.clients:
            self.clients[client_id] = Connection(client_id, conn)
            self.client_ids[conn] = client_id
            self.rsockets.append(conn)
            self.wsockets.append(conn)

    def destroy_client(self, client_id: str):
        logger.info("[MAINSERVER] destroy client {}".format(client_id))

        if client_id in self.clients:
            c = self.clients[client_id]
            remove_ids = []
            for id, client in self.id2client.items():
                if c is client:
                    remove_ids.append(id)
            for id in remove_ids:
                del self.id2client[id]
            del self.clients[client_id]

    def load_rules(self, file: str):
        with open(file, 'r') as fp:
            for line in fp.readlines():
                line = line.strip()
                rule = Rule()
                if rule.parse_string(line) == 0:
                    self.create_server(rule)

    def start(self):
        while True:
            rsockets, wsockets, xsockets = select(self.rsockets, self.wsockets, self.xsockets, 0)
            for rsocket in rsockets:
                if rsocket is self.socket:
                    conn, addr = rsocket.accept()
                    client_id = "{}:{}".format(addr[0], addr[1])
                    self.create_client(client_id, conn)

                else:
                    client_id = self.client_ids[rsocket]
                    client = self.clients[client_id]
                    data = rsocket.recv(1024 * 10)
                    if len(data) > 0:
                        util.push(client.output_buf, data)
                        msg, ec = util.pop_msg(client.output_buf)
                        if ec == 0 and msg.id in self.id2server:
                            if self.id2server[msg.id].push_msg(msg) != 0:
                                del self.id2server[msg.id]
                    else:
                        self.destroy_client(client_id)

            for wsocket in self.wsockets:
                client_id = self.client_ids[wsocket]
                client = self.clients[client_id]
                if len(client.input_buf) == 0:
                    continue
                size = client.conn.send(client.input_buf)
                if size > 0:
                    util.pop(client.input_buf, size)

            for rule, server in self.rules.items():
                server.poll()
                msg, ec = server.pop_msg()
                if ec != 0:
                    continue

                logger.debug("[MAINSERVER] pop msg {} {}".format(rule, msg.__dict__))

                if msg.type == MsgType.OPEN_CONN:
                    msg.data = str.encode(rule.__str__(), encoding='utf-8')
                    self.id2server[msg.id] = server
                    self.id2client[msg.id] = self.choose_client()

                if msg.id in self.id2client:
                    client = self.id2client[msg.id]
                    util.push_msg(client.input_buf, msg.type, msg.id, msg.data)


if __name__ == '__main__':
    ms = MainServer('cfg.json')
    ms.load_rules(ms.config.rule_file)
    ms.start()
