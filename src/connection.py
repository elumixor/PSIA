import socket
import struct
import time
import zlib
from threading import Thread
from typing import Callable

from utils import log

WINDOW_SIZE = 4

HEADER_SIZE = 20
MAX_PACKET_SIZE = 1024
CRC_SIZE = 4
MAX_DATA_SIZE = MAX_PACKET_SIZE - HEADER_SIZE - CRC_SIZE


class Listener:
    def __init__(self, receive_socket: socket.socket, request_handler: Callable[[bytes], None]):
        self.should_exit = False

        def listener():
            while not self.should_exit:
                try:
                    data, _ = receive_socket.recvfrom(MAX_PACKET_SIZE)
                    request_handler(data)
                except socket.timeout:
                    ...

        self.thread = Thread(target=listener)
        self.thread.start()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        if not self.thread.is_alive():
            return

        self.should_exit = True
        self.thread.join()

    def close(self):
        self.__exit__()

    def wait(self):
        self.thread.join()


class Connection:
    def __init__(self, my_ip: str, my_port: int, remote_ip: str, remote_port: int, timeout: int):
        self.my_ip = my_ip
        self.my_port = my_port
        self.remote_ip = remote_ip
        self.remote_port = remote_port

        self.timeout = timeout

        self.send_socket: socket.socket
        self.receive_socket: socket.socket

        self.listener: Listener

        self.handler = None
        self._remote_status = None
        self.status = None

        self._handlers = dict()

    def __enter__(self):
        self.send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0).__enter__()
        self.send_socket.settimeout(self.timeout)

        self.receive_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0).__enter__()
        self.receive_socket.bind((self.my_ip, self.my_port))
        self.receive_socket.settimeout(0.1)  # set a small timeout on the receive socket

        # Create a request listener in a separate thread
        # pass a callback for request handling
        self.listener = Listener(self.receive_socket, self.handle_request).__enter__()

        return self

    def __exit__(self, *args):
        self.send_socket.__exit__()
        self.listener.__exit__()

    def handle_request(self, data: bytes):
        # print(data)
        # print(data)
        data, crc = data[:-4], data[-4:]
        crc, = struct.unpack("I", crc)

        if zlib.crc32(data) != crc:
            log.info("crc do not match")
            return

        if data == b"get status":
            self.send(self.status)
            return

        if self.handler == "awaiting status":
            self._remote_status = data
            self.handler = None
            return

        header, data = data[:HEADER_SIZE], data[HEADER_SIZE:]

        # remove padded null bytes
        if b"\0" in header:
            header = header[:header.index(b"\0")]

        if header not in self._handlers:
            return

        assert header in self._handlers

        # Find the handler and run it
        self._handlers[header](data)

    def add_handler(self, header: bytes, handler: Callable[[bytes], None]):
        assert header not in self._handlers

        self._handlers[header] = handler

    def send(self, data: bytes):
        assert len(data) <= MAX_PACKET_SIZE

        self.send_socket.sendto(data + struct.pack("I", zlib.crc32(data)), (self.remote_ip, self.remote_port))

    def send_message(self, header: bytes, data: bytes):
        assert len(header) <= HEADER_SIZE

        # pad header with null bytes
        header += b"\0" * (HEADER_SIZE - len(header))

        self.send(header + data)

    @property
    def remote_status(self):
        self.handler = "awaiting status"

        self._remote_status = None
        self.send(b"get status")

        while self._remote_status is None:
            time.sleep(0.1)
            self.send(b"get status")

        # print(self._remote_status)
        return self._remote_status
