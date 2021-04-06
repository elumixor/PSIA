import hashlib
import struct
import time
from typing import Dict

import rtypes
from connection import Connection, HEADER_SIZE
from utils import read_yaml, log


class Receiver(Connection):
    def __init__(self):
        def on_received(data):
            rtype, data = data[:HEADER_SIZE], data[HEADER_SIZE:]

            # remove padded null bytes
            if b"\0" in rtype:
                rtype = rtype[:rtype.index(b"\0")]

            # Update remote status
            if rtype == rtypes.header:
                log.info("request: header")
                # Ignore repeated requests
                if self.status is not None:
                    self.send_status()
                    return

                chunks_count, self.md5 = data[:4], data[4:]
                chunks_count, = struct.unpack("i", chunks_count)

                print(f"chunks_count = {chunks_count}")

                self.pending = list(range(chunks_count))
                self.received = []

                self.status = self.pending, self.received
                self.chunks = dict()

                self.send_status()

            elif rtype == rtypes.packet:
                log.info("request: packet")

                index, chunk = data[:4], data[4:]
                index, = struct.unpack("i", index)

                pending, received = self.status

                # Ignore duplicate packets
                if index in self.chunks:
                    self.send_status()
                    return

                received.append(index)
                pending.remove(index)

                log(f"pending: {len(pending):5}, received: {len(received):5}")

                self.chunks[index] = chunk

                self.send_status()

        super().__init__(my_ip, my_port, remote_ip, remote_port, timeout, on_received)

        self.status = None
        self.md5: bytes
        self.chunks: Dict[int, bytes]

    def send_message(self, rtype, data: bytes):
        assert len(rtype) <= HEADER_SIZE

        # pad header with null bytes
        rtype += b"\0" * (HEADER_SIZE - len(rtype))

        self.send(rtype + data)

    def send_status(self):
        pending, received = self.status

        data = struct.pack("ii", len(pending), len(received))

        if pending:
            data += struct.pack(f"{len(pending)}i", *pending)

        if received:
            data += struct.pack(f"{len(received)}i", *received)

        self.send_message(rtypes.status, data)


if __name__ == '__main__':
    # Read configuration
    config = read_yaml("../config.yaml")

    my_ip, my_port = config.receiver_ip, config.port.data.target
    remote_ip, remote_port = config.sender_ip, config.port.acknowledgement.source

    file_name = config.file_name.receiver
    timeout = config.timeout

    window = config.window

    with Receiver() as receiver:
        log("Receiver started")
        while receiver.status is None or receiver.status[0]:
            time.sleep(1)

        log.success("All packets received")
        received = receiver.status[1]

        file_bytes = b""
        for i in range(len(received)):
            file_bytes += receiver.chunks[i]

        # Note that this is a redundancy, because there is
        #  actually no possibility to have an MD5 failure,
        if receiver.md5 == hashlib.md5(file_bytes).digest():
            log.success("MD5 match. Receive successful")

        # note: never gonna happen
        else:
            log.error("MD5 mismatch")
            exit(1)

        # Shout out status for one second
        time.sleep(1)

    with open(file_name, "wb") as file:
        file.write(file_bytes)
