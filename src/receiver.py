import hashlib
import struct
import sys
import time

from connection import Connection
from utils import read_yaml, log

if __name__ == '__main__':
    # Read configuration
    config = read_yaml("../config.yaml")

    my_ip, my_port = config["receiver_ip"], config["port"]["data"]["target"]
    remote_ip, remote_port = config["sender_ip"], config["port"]["acknowledgement"]["source"]

    file_name = config["file_name"]["receiver"]
    timeout = config["timeout"]

    with Connection(my_ip, my_port, remote_ip, remote_port, timeout) as connection:
        file_bytes = None
        md5 = None
        chunks_count = None
        chunk_index = None
        should_close = False


        def on_header(header: bytes):
            global file_bytes, chunks_count, md5, chunk_index

            chunks_count, md5 = header[:4], header[4:]
            chunks_count, = struct.unpack("i", chunks_count)

            log(f"Header received. Chunks count: {chunks_count}")

            chunk_index = 0
            file_bytes = b""

            connection.status = b"header received"


        def on_packet(packet: bytes):
            global should_close, chunk_index, file_bytes

            index, packet = packet[:4], packet[4:]
            index, = struct.unpack("i", index)

            if index != chunk_index:
                return

            file_bytes += packet

            log(f"Received chunk {chunk_index}")

            if chunk_index == chunks_count - 1:
                # Basically, MD5 check is redundant, as we've guaranteed
                # the correct order of the individual packets and their
                # integrity
                if md5 == hashlib.md5(file_bytes).digest():
                    connection.status = b"md5 ok"

                    with open(file_name, "wb") as file:
                        file.write(file_bytes)

                    log.success("Receive successful")
                    should_close = True
                else:
                    connection.status = b"md5 error"
                    log.error("MD5 error", file=sys.stderr)
            else:
                connection.status = b"received " + struct.pack("i", chunk_index)
                chunk_index += 1


        def on_reset(_):
            global file_bytes, md5
            file_bytes = b""
            connection.status = b"receive ready"


        connection.add_handler(b"header", on_header)
        connection.add_handler(b"packet", on_packet)
        connection.add_handler(b"reset", on_reset)

        connection.status = b"receive ready"

        while not should_close:
            time.sleep(0.1)

        # Give sender some time to get to know the current "OK" status
        time.sleep(2)
