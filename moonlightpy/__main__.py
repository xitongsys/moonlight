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
        network_name, addr, port = sys.argv[2], sys.argv[3], int(sys.argv[4])
        c = client.Client(network_name, addr, port)
        c.start()

    else:
        raise ValueError("unknown role {}".format(role))
