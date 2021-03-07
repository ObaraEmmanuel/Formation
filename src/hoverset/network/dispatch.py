import selectors
import struct
import socket
from hoverset.network import protocols
from hoverset.network.utils import json_decode

protocol_map = {
    # Protocol name: Protocol class
    protocols.FileTransfer.name: protocols.FileTransfer,
    protocols.HostIdentity.name: protocols.HostIdentity,
}

REQUIRED_HEADERS = (
    "byteorder",
    "content-encoding",
    "content-protocol",
    "content-size",
)


class MessageHandle:
    HEADER_LEN = 2

    def __init__(self, selector, sock, addr, protocol_handler=None):
        self.selector = selector
        self.sock: socket.socket = sock
        self.addr = addr
        self._recv_total = 0
        self._recv_buffer = b""
        self._send_buffer = b""
        self._json_header_len = None
        self.json_header = None
        self.request = None
        self.response_created = False
        self.protocol_handler = protocol_handler

    def _set_selector_events_mask(self, mode):
        """Set selector to listen for events: mode is 'r', 'w', or 'rw'."""
        if mode == "r":
            events = selectors.EVENT_READ
        elif mode == "w":
            events = selectors.EVENT_WRITE
        elif mode == "rw":
            events = selectors.EVENT_READ | selectors.EVENT_WRITE
        else:
            raise ValueError(f"Invalid events mask mode {repr(mode)}.")
        self.selector.modify(self.sock, events, data=self)

    def _read(self):
        try:
            # Should be ready to read
            data = self.sock.recv(4096)
            print("received {} bytes ".format(len(data)))
        except BlockingIOError:
            # Resource temporarily unavailable (errno EWOULDBLOCK)
            print("blocking error")
            pass
        else:
            if data:
                self._recv_buffer += data
            else:
                if self.protocol_handler is not None and not self.protocol_handler.has_response:
                    self.protocol_handler.complete()
                    print("Transfer complete")

    def _write(self):
        self._send_buffer += self.protocol_handler.read()
        if self._send_buffer:
            # print("sending", repr(self._send_buffer), "to", self.addr)
            try:
                # Should be ready to write
                sent = self.sock.send(self._send_buffer)
                print("sending {} bytes".format(sent))
            except BlockingIOError:
                # Resource temporarily unavailable (errno EWOULDBLOCK)
                print("blocking")
                pass
            else:
                self._send_buffer = self._send_buffer[sent:]
                # Close when the buffer is drained. The response has been sent.
                if sent and not self._send_buffer:
                    self.protocol_handler.complete()
                    self.close()

    def process_events(self, mask):
        if mask & selectors.EVENT_READ:
            self.read()
        if mask & selectors.EVENT_WRITE:
            self.write()

    def read(self):
        # self._read()
        # self._json_header_len is None and self.process_protoheader()
        # self._json_header_len is not None and self.json_header is None and self.process_json_header()
        # self.json_header is not None and self.process_request()
        self._read()
        if self._json_header_len is None:
            self.process_protoheader()

        if self._json_header_len is not None:
            if self.json_header is None:
                self.process_json_header()

        if self.json_header:
            self.process_request()

    def write(self):
        if self.protocol_handler.has_response:
            self._write()

    def close(self):
        # print("closing connection to", self.addr)
        try:
            self.selector.unregister(self.sock)
        except Exception as e:
            print(
                f"error: selector.unregister() exception for",
                f"{self.addr}: {repr(e)}",
            )

        try:
            self.sock.close()
        except OSError as e:
            print(
                f"error: socket.close() exception for",
                f"{self.addr}: {repr(e)}",
            )
        finally:
            # Delete reference to socket object for garbage collection
            self.sock = None

    def process_protoheader(self):
        # Process fixed length header
        if len(self._recv_buffer) >= MessageHandle.HEADER_LEN:
            self._json_header_len = struct.unpack(
                ">H", self._recv_buffer[:MessageHandle.HEADER_LEN]
            )[0]
            self._recv_buffer = self._recv_buffer[MessageHandle.HEADER_LEN:]

    def process_json_header(self):
        # Process variable length header
        header_len = self._json_header_len
        if len(self._recv_buffer) >= header_len:
            self.json_header = json_decode(self._recv_buffer[:header_len], "utf-8")
            self._recv_buffer = self._recv_buffer[header_len:]
            if any([i not in self.json_header for i in REQUIRED_HEADERS]):
                raise ValueError(f'Missing one or more required headers".')
            handler_protocol = protocol_map.get(self.json_header["content-protocol"])
            if handler_protocol is not None:
                self.protocol_handler = handler_protocol(self.json_header)
            else:
                raise ValueError("Protocol {} is not recognized".format(self.json_header["content-protocol"]))

    def process_request(self):
        content_len = self.json_header.get("content-size", 0)
        self._recv_total += len(self._recv_buffer)
        data = self._recv_buffer
        # Empty buffer
        self._recv_buffer = b""
        if self._recv_total >= content_len:
            # Set selector to listen for write events, we're done reading.
            # self.protocol_handler.complete()
            self._set_selector_events_mask("w")
            return
        self.protocol_handler.receive(data)
