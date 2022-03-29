import json
from socket import *
from select import *
import logger


class User:
    def __init__(self, name: str, password: str, port: int):
        self.name = name
        self.password = password
        self.port = port


class Config:
    def __init__(self, config_file: str = None):
        self.addr = "0.0.0.0"
        self.port = 9001
        self.max_num = 1024
        self.users = {}

        if config_file:
            with open(config_file) as fp:
                cfg = json.load(fp)
                self.addr = cfg['addr']
                self.port = cfg['port']
                self.max_num = cfg['max_num']
                for name in cfg['users']:
                    self.users[name] = User(cfg['users']['name'], cfg['users']['password'], cfg['users']['port'])


class MainServer:
    def __init__(self, config_file: str = None):
        self.config = Config(config_file)
        self.main_socket = socket(family=AF_INET, type=SOCK_STREAM, proto=0)
        self.main_socket.bind((self.config.addr, self.config.port))
        self.main_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, True)
        self.main_socket.listen(self.config.max_num)

        logger.info("luarel start: {}".format(json.dumps(self.config.__dict__)))

        self.revents, self.wevents, self.xevents = [self.main_socket], [], []

    def start(self):
        rsockets, wsockets, xsockets = select(self.revents, self.wevents, self.xevents)
        for rsocket in rsockets:
            if rsocket is self.main_socket:
                conn, addr = rsocket.accept()
                self.revents.append(conn)

            else:
                data = rsocket.recv()

    def handler(self, data):




if __name__ == '__main__':
    ms = MainServer()
