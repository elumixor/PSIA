import socket
import struct
import zlib
from threading import Thread
from typing import Callable

from utils import log

HEADER_SIZE = 10
MAX_PACKET_SIZE = 1024
CRC_SIZE = 4
MAX_DATA_SIZE = MAX_PACKET_SIZE - HEADER_SIZE - CRC_SIZE


class Connection:
    def __init__(self, my_ip: str, my_port: int, remote_ip: str, remote_port: int, timeout: int, on_received: Callable[[bytes], None]):
        self.my_ip = my_ip
        self.my_port = my_port
        self.remote_ip = remote_ip
        self.remote_port = remote_port

        self.timeout = timeout

        self.send_socket: socket.socket
        self.receive_socket: socket.socket

        self.should_exit = False

        self.on_received = on_received
        self.thread: Thread

    def __enter__(self):
        self.send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0).__enter__()
        self.send_socket.settimeout(self.timeout)

        self.receive_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0).__enter__()
        self.receive_socket.bind((self.my_ip, self.my_port))
        self.receive_socket.settimeout(0.1)  # set a small timeout on the receive socket

        # Create a request listener in a separate thread
        # pass a callback for request handling
        def listener():
            while not self.should_exit:
                try:
                    data, _ = self.receive_socket.recvfrom(MAX_PACKET_SIZE)

                    data, crc = data[:-CRC_SIZE], data[-CRC_SIZE:]
                    crc, = struct.unpack("I", crc)

                    if zlib.crc32(data) != crc:
                        log.info("crc do not match")
                        continue

                    self.on_received(data)
                except socket.timeout:
                    ...

        self.thread = Thread(target=listener)
        self.thread.start()

        return self

    def __exit__(self, *args):
        self.send_socket.__exit__()

        self.should_exit = True
        self.thread.join()

        self.receive_socket.__exit__(*args)

    def send(self, data: bytes):
        assert len(data) <= MAX_PACKET_SIZE

        self.send_socket.sendto(data + struct.pack("I", zlib.crc32(data)), (self.remote_ip, self.remote_port))
