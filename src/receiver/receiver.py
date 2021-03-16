import socket
import struct
import zlib


class Receiver:

    def __init__(self, ip, port, max_attempts, timeout, verbose=False):
        self.ip = ip
        self.port = port
        self.max_attempts = max_attempts
        self.socket = None
        self.address = None
        self.timeout = timeout
        self.verbose = verbose
        self.last_packet_number = -1

    def __enter__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM).__enter__()
        self.socket.bind((self.ip, self.port))
        self.socket.settimeout(self.timeout)
        return self

    def __exit__(self, *args):
        self.socket.__exit__()

    def receive(self, raw_data_count: int):
        for attempt in range(1, self.max_attempts + 1):
            try:
                # We receive the raw data, plus the crc32 and packet_number, which is 8 bytes
                packet, self.address = self.socket.recvfrom(raw_data_count + 8)

                # Once received, we will check the crc32 and store the packet number
                crc32, = struct.unpack("I", packet[-8:-4])
                packet_number, = struct.unpack("i", packet[-4:])
                packet_number_bytes = packet[-4:]
                data_bytes = packet[:-8]

                if crc32 == zlib.crc32(data_bytes) and packet_number == self.last_packet_number + 1:
                    self.last_packet_number = packet_number
                    self.send_ok(packet_number_bytes)
                    return data_bytes

                if self.verbose:
                    print(f"Attempt {attempt}: Crc32 keys do not match. Requesting resend.")

                self.send_error(packet_number_bytes)
            except socket.timeout:
                if self.verbose:
                    print(f"Confirmation: error (timeout) (receiver)")

        raise RuntimeError(f"Failed after {self.max_attempts} attempts")

    def send_ok(self, packet_number: bytes):
        self.socket.sendto(struct.pack("?", True) + packet_number, self.address)

    def send_error(self, packet_number: bytes):
        self.socket.sendto(struct.pack("?", False) + packet_number, self.address)
