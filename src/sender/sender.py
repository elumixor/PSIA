import socket
import struct
import zlib


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

    @property
    def send_succeeded(self):
        """
        Asks for the confirmation from the server if the packet was successfully received
        """
        try:
            response, _ = self.socket.recvfrom(1)
            ok = struct.unpack("?", response)

            if self.verbose and not ok:
                print("Confirmation: error")

            return ok
        except socket.timeout:
            # If time out, we assume that the server has never obtained our initial packet
            # So we re-send the data once again. We thus treat a timeout similarly to the
            # hash check failure
            if self.verbose:
                print(f"Confirmation: error (timeout)")

            return False

    def send(self, data: bytes):
        """
        Sends a packet with a 4 bytes of crc32 added in the end.
        Awaits for confirmation from the receiver.

        :raises RuntimeError: in case of timeout, or after the maximum of allowed failures elapsed
        :param data: Byte data to be sent
        """
        crc32 = zlib.crc32(data)
        packet = data + struct.pack("I", crc32)

        for attempt in range(1, self.max_attempts + 1):
            self.socket.sendto(packet, (self.ip, self.port))

            if self.send_succeeded:
                return

        raise RuntimeError(f"Failed after {self.max_attempts} attempts")
