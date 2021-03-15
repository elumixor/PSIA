import socket
import struct
import zlib


class Receiver:

    def __init__(self, ip, port, max_attempts, verbose=False):
        self.ip = ip
        self.port = port
        self.max_attempts = max_attempts
        self.socket = None
        self.address = None
        self.verbose = verbose

    def __enter__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM).__enter__()
        self.socket.bind((self.ip, self.port))
        return self

    def __exit__(self, *args):
        self.socket.__exit__()

    def receive(self, raw_data_count: int):
        for attempt in range(1, self.max_attempts + 1):
            # We receive the raw data, plus the crc32, which is 4 bytes
            packet, self.address = self.socket.recvfrom(raw_data_count + 4)

            # Once received, we will check the crc32
            crc32, = struct.unpack("I", packet[-4:])
            data_bytes = packet[:-4]

            if crc32 == zlib.crc32(data_bytes):
                self.send_ok()
                return data_bytes

            if self.verbose:
                print(f"Attempt {attempt}: Crc32 keys do not match. Requesting resend.")

            self.send_error()

        raise RuntimeError(f"Failed after {self.max_attempts} attempts")

    def send_ok(self):
        self.socket.sendto(struct.pack("?", True), self.address)

    def send_error(self):
        self.socket.sendto(struct.pack("?", False), self.address)
