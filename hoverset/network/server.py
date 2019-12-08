import socket
import selectors
import threading
import traceback
from hoverset.network.dispatch import MessageHandle
from hoverset.network.utils import get_ip

DEFAULT_PORT = 65432


class ServerSystem(threading.Thread):
    available = []

    @staticmethod
    def create(host=None, port=DEFAULT_PORT):
        if host is None:
            host = get_ip()
        for server in ServerSystem.available:
            if server.addr == (host, port):
                return server
        return ServerSystem(host, port)

    def __init__(self, host, port=DEFAULT_PORT):
        # Do not create a server_system using this initializer
        # Use create method instead
        super().__init__()
        self.selector = selectors.DefaultSelector()
        self.addr = (host, port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Avoid bind() exception: OSError: [Errno 48] Address already in use
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((host, port))
        print("Listening at {}: {}...".format(host, port))
        self.sock.listen()
        self.sock.setblocking(False)
        self.selector.register(self.sock, selectors.EVENT_READ, data=None)
        ServerSystem.available.append(self)

    def accept(self, sock: socket.socket) -> None:
        conn, addr = sock.accept()  # Should be ready to read
        print("accepted connection from", addr)
        conn.setblocking(False)
        message = MessageHandle(self.selector, conn, addr)
        self.selector.register(conn, selectors.EVENT_READ, data=message)

    def run(self) -> None:
        while True:
            events = self.selector.select(timeout=None)
            for key, mask in events:
                if key.data is None:
                    self.accept(key.fileobj)
                else:
                    message = key.data
                    try:
                        message.process_events(mask)
                    except Exception:
                        # print(
                        #     "main: error: exception for",
                        #     f"{message.addr}:\n{traceback.format_exc()}",
                        # )
                        message.close()


if __name__ == "__main__":
    ServerSystem.create().start()
