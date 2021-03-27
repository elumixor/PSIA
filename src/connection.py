import socket
import struct
import sys
import zlib


class Connection:
    def __init__(self, my_ip: str, my_port: int, remote_ip: str, remote_port: int, timeout=0.2, attempts=1):
        self.my_ip = my_ip
        self.my_port = my_port
        self.remote_ip = remote_ip
        self.remote_port = remote_port

        self.timeout = timeout
        self.attempts = attempts

        self.send_socket: socket.socket
        self.receive_socket: socket.socket

    def __enter__(self):
        self.send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0).__enter__()
        self.send_socket.settimeout(self.timeout)

        self.receive_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0).__enter__()
        self.receive_socket.bind((self.my_ip, self.my_port))
        self.receive_socket.settimeout(self.timeout)

        return self

    def __exit__(self, *args):
        self.send_socket.__exit__()
        self.receive_socket.__exit__()

    def send_packet(self, data: bytes):
        # Add crc32 to the data
        crc32 = zlib.crc32(data)
        packet = data + struct.pack("I", crc32)

        # Try `self.attempts` times
        for _ in range(self.attempts):
            # Send the actual packet
            self.send_socket.sendto(packet, (self.remote_ip, self.remote_port))

            # Receive confirmation
            try:
                ok, _ = self.receive_socket.recvfrom(1)
                ok, = struct.unpack("?", ok)

            except socket.timeout:
                print("error: timeout", file=sys.stderr)
                continue

            if ok:
                print("ok")
                return

            print("error: crc32 do not match", file=sys.stderr)

        # If after `self.attempts` send did not succeed, raise an error
        raise RuntimeError(f"Send did not succeed after {self.attempts} attempts")

    def receive(self, raw_bytes_count: int, timeout=True, crc=True):
        # We receive the raw data, plus the crc32, which is 4 bytes
        total_count = raw_bytes_count if not crc else raw_bytes_count + 4

        for _ in range(self.attempts):
            if timeout:
                try:
                    packet, _ = self.receive_socket.recvfrom(total_count)
                except socket.timeout:
                    print("error: timeout", file=sys.stderr)
                    continue

            else:
                # If timeout is False, try until received
                while True:
                    try:
                        packet, _ = self.receive_socket.recvfrom(total_count)
                        break
                    except socket.timeout:
                        ...

            if not crc:
                return packet

            # Once received, check the crc32
            crc32, = struct.unpack("I", packet[-4:])
            data_bytes = packet[:-4]

            if crc32 == zlib.crc32(data_bytes):
                print("ok")
                self.send_ok()
                return data_bytes

            print("error: crc32 do not match", file=sys.stderr)
            self.send_error()

        raise RuntimeError(f"Receive did not succeed after {self.attempts} attempts")

    def send_ok(self):
        self.send_socket.sendto(struct.pack("?", True), (self.remote_ip, self.remote_port))

    def send_error(self):
        self.send_socket.sendto(struct.pack("?", False), (self.remote_ip, self.remote_port))
