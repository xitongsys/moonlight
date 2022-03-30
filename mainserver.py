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

    def create_client(self, id: str, conn: socket):
        if id not in self.clients:
            self.clients[id] = Connection(id, conn)
            self.rsockets.append(conn)
            self.wsockets.append(conn)

    def destroy_client(self, client_id: str):
        if client_id in self.clients:
            c = self.clients[client_id]
            for id, client in self.id2client.items():
                if c is client:
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
        rsockets, wsockets, xsockets = select(self.rsockets, self.wsockets, self.xsockets, 0)
        for rsocket in rsockets:
            if rsocket is self.socket:
                conn, addr = rsocket.accept()
                self.create_client(addr, conn)

            else:
                data = rsocket.recv(1024 * 10)
                client_id = self.client_ids[rsocket]
                client = self.clients[client_id]
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

        for rule, server in self.rules:
            msg, ec = server.pop_msg()
            if msg.type == MsgType.OPEN_CONN:
                msg.data = bytes(rule.__str__())
                self.id2server[msg.id] = server
                self.id2client[msg.id] = self.choose_client()

            if ec == 0 and msg.id in self.id2clients:
                client = self.id2clients[msg.id]
                util.push_msg(client.input_buf, msg.type, msg.id, msg.data)


if __name__ == '__main__':
    ms = MainServer()
