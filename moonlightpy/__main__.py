import sys
from . import server
from . import client

if __name__ == '__main__':
    role = sys.argv[1]

    if role == 'server':
        cfg_file = sys.argv[2]
        s = server.Server(cfg_file)
        s.start()

    elif role == 'client':
        addr, port = sys.argv[2], int(sys.argv[3])
        c = client.Client(addr, port)
        c.start()

    else:
        raise ValueError("unknown role {}".format(role))
