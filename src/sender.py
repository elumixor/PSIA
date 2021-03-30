import hashlib
import struct
import sys
from math import ceil

from connection import Connection
from utils import read_yaml

if __name__ == '__main__':
    # Read configuration
    config = read_yaml("../config.yaml")

    my_ip, my_port = config["sender_ip"], config["port"]["acknowledgement"]["target"]
    remote_ip, remote_port = config["receiver_ip"], config["port"]["data"]["source"]

    file_name = config["file_name"]["sender"]
    chunk_size = config["chunk_size"]
    timeout = config["timeout"]
    attempts = config["attempts"]

    total_attempts = config["total_attempts"]

    # Read the whole file as bytes
    with open(file_name, "rb") as file:
        file_bytes = file.read(-1)

    # We must send the number of chunks to the server,
    # so that they know how many messages to receive
    chunks_count = ceil(len(file_bytes) / chunk_size)

    with Connection(my_ip, my_port, remote_ip, remote_port, timeout, attempts) as connection:
        # Try several times
        for _ in range(total_attempts):
            try:
                # Send the chunk size as a byte array
                connection.send_packet(struct.pack("i", chunks_count))

                # Send the MD5 of the whole data
                file_md5_key = hashlib.md5(file_bytes)
                connection.send_packet(file_md5_key.digest())

                # Send bytes by chunks
                for i in range(chunks_count):
                    chunk = file_bytes[i * chunk_size: (i + 1) * chunk_size]
                    connection.send_packet(chunk)
                    print(f"{i + 1}/{chunks_count} ok")

                # Receive the confirmation for the whole file
                if connection.receive(1, crc=False):
                    print("Send ok")
                    exit(0)

            except RuntimeError as e:
                print(e)

            print("Attempt failed", file=sys.stderr)

        print(f"Did not succeed after {total_attempts} attempts", file=sys.stderr)
