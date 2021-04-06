import hashlib
import struct
import time
from math import ceil

import rtypes
from connection import Connection, MAX_DATA_SIZE, HEADER_SIZE
from utils import read_yaml, log


class Sender(Connection):
    def __init__(self):
        def on_received(data):
            rtype, data = data[:HEADER_SIZE], data[HEADER_SIZE:]

            # remove padded null bytes
            if b"\0" in rtype:
                rtype = rtype[:rtype.index(b"\0")]

            # Update remote status
            if rtype == rtypes.status:
                num_pending, num_received = struct.unpack("ii", data[:8])

                end_pending = 8 + 4 * num_pending

                pending = [] if num_pending == 0 else struct.unpack(f"{num_pending}i", data[8:end_pending])
                received = [] if num_received == 0 else struct.unpack(f"{num_received}i", data[end_pending:end_pending + 4 * num_received])

                self.remote_status = [pending, received]

        super().__init__(my_ip, my_port, remote_ip, remote_port, timeout, on_received)

        self.remote_status = None

    def send_message(self, rtype, data: bytes):
        assert len(rtype) <= HEADER_SIZE

        # pad header with null bytes
        rtype += b"\0" * (HEADER_SIZE - len(rtype))

        self.send(rtype + data)


if __name__ == '__main__':
    # Read configuration
    config = read_yaml("../config.yaml")

    my_ip, my_port = config.sender_ip, config.port.acknowledgement.target
    remote_ip, remote_port = config.receiver_ip, config.port.data.source

    file_name = config.file_name.sender
    chunk_size = MAX_DATA_SIZE - 4  # chunk index
    timeout = config.timeout

    window = config.window

    # Read the whole file as bytes
    with open(file_name, "rb") as file:
        file_bytes = file.read(-1)

    # We must send the number of chunks to the server,
    # so that they know how many messages to receive
    chunks_count = ceil(len(file_bytes) / chunk_size)
    md5 = hashlib.md5(file_bytes).digest()

    # Split data in chunks
    chunks = {i: file_bytes[i * chunk_size: (i + 1) * chunk_size] for i in range(chunks_count)}

    with Sender() as sender:
        log("Sending header")
        while sender.remote_status is None:
            sender.send_message(rtypes.header, struct.pack("i", chunks_count) + md5)
            time.sleep(0.05)  # wait before refresh

        while True:
            pending, received = sender.remote_status

            if not pending:
                log.success("All packets received")
                break

            log(f"pending: {len(pending):5}, received: {len(received):5}")

            # select pending chunks
            chunks_to_send = [(i, chunks[i]) for i in pending][:window]

            # send given chunks
            for i, chunk in chunks_to_send:
                sender.send_message(rtypes.packet, struct.pack("i", i) + chunk)

            time.sleep(0.05)  # wait before refresh
