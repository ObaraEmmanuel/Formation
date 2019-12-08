"""
Network utility functions for use by hoverset network systems
"""

import struct
import sys
import json
import io
import socket


def json_encode(header):
    return json.dumps(header, ensure_ascii=False).encode(header.get("content-encoding", "utf-8"))


def json_decode(header_bytes, encoding="utf-8"):
    wrapper = io.TextIOWrapper(
        io.BytesIO(header_bytes), encoding=encoding, newline=""
    )
    try:
        obj = json.load(wrapper)
    finally:
        wrapper.close()
    return obj


def prepare_header(header):
    header["byteorder"] = sys.byteorder
    header["content-encoding"] = header.get("content-encoding", "utf-8")
    header_bytes = json_encode(header)
    message_hdr = struct.pack(">H", len(header_bytes))
    return message_hdr + header_bytes


def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception as e:
        print(e)
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip
