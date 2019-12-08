import sys
import socket
import selectors
import threading
import traceback
import json
import struct
import hoverset.network.dispatch as dispatch


class SimpleClient(threading.Thread):

    def __init__(self, host, port):
        super().__init__()
        self.addr = (host, port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.buffer = b''
        self.protocol = None

    def connect(self, protocol):
        self.protocol = protocol

    def run(self) -> None:
        protocol = self.protocol
        self.sock.connect(self.addr)
        print("connected to {}: {}".format(*self.addr))
        self.buffer += protocol.read()
        total = 0
        while self.buffer:
            self.sock.sendall(self.buffer)
            total += len(self.buffer)
            self.buffer = b''
            self.buffer += protocol.read()

        data = self.sock.recv(4096)
        t = 0
        while data:
            t += len(data)
            protocol.receive(data)
            data = self.sock.recv(4096)
        protocol.complete()
        print("sent {} bytes".format(total))
        print("received {} bytes".format(t))
        self.close()

    def close(self):
        self.sock.close()


class ClientSystem(threading.Thread):

    def __init__(self):
        super().__init__()
        self.selector = selectors.DefaultSelector()
        self.connections = []

    def connect(self, host, port, protocol_handler):
        addr = (host, port)
        print("starting connection to", addr)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setblocking(False)
        sock.connect_ex(addr)
        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        self.connections.append(sock)
        message = dispatch.MessageHandle(self.selector, sock, addr, protocol_handler)
        self.selector.register(sock, events, data=message)

    def run(self) -> None:
        while True:
            events = self.selector.select(timeout=1)
            for key, mask in events:
                message = key.data
                try:
                    message.process_events(mask)
                except Exception:
                    print(
                        "main: error: exception for",
                        f"{message.addr}:\n{traceback.format_exc()}",
                    )
                    message.close()
            # Check for a socket being monitored to continue.
            if not self.selector.get_map():
                break
