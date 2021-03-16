import socket
import struct
import zlib
import random

DROP_RATE = 10
ERROR_RATE = 10


class Sender:
    def __init__(self, ip, port, max_attempts, timeout, verbose=False):
        self.ip = ip
        self.port = port
        self.max_attempts = max_attempts
        self.timeout = timeout
        self.socket = None
        self.verbose = verbose

    def __enter__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0).__enter__()
        self.socket.settimeout(self.timeout)
        return self

    def __exit__(self, *args):
        self.socket.__exit__()

    # @property
    def send_succeeded(self, packet_num_bytes):
        """
        Asks for the confirmation from the server if the packet was successfully received
        """
        try:
            response, _ = self.socket.recvfrom(5)
            ok, = struct.unpack("?", response[:1])
            rec_packet_number = response[1:]

            if self.verbose and not ok:
                print("Confirmation: error")

            if rec_packet_number == struct.pack("i", 9999):
                return True

            if rec_packet_number != packet_num_bytes:
                return False

            return ok
        except socket.timeout:
            # If time out, we assume that the server has never obtained our initial packet
            # So we re-send the data once again. We thus treat a timeout similarly to the
            # hash check failure
            if self.verbose:
                print(f"Confirmation: error (timeout)")

            return False

    def send(self, data: bytes, packet_number: int):
        """
        Sends a packet with a 4 bytes of crc32 added in the end.
        Awaits for confirmation from the receiver.

        :raises RuntimeError: in case of timeout, or after the maximum of allowed failures elapsed
        :param data: Byte data to be sent
        """
        crc32 = zlib.crc32(data)
        packet_num_bytes = struct.pack("i", packet_number)
        packet = data + struct.pack("I", crc32) + packet_num_bytes

        for attempt in range(1, self.max_attempts + 1):
            message = packet

            # simulates data corruption
            if random.random() < (ERROR_RATE / 100):
                print("Simulating packet corruption")
                message = bytearray(message)
                message[1] = 1

            # simulates packet loss
            if random.random() > (DROP_RATE / 100):
                self.socket.sendto(message, (self.ip, self.port))
            else:
                print("Simulating packet loss")

            if self.send_succeeded(packet_num_bytes):
                return

        raise RuntimeError(f"Failed after {self.max_attempts} attempts")
