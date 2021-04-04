import hashlib
import struct
import time
from math import ceil

from connection import Connection, MAX_DATA_SIZE, WINDOW_SIZE
from utils import read_yaml, log

if __name__ == '__main__':
    # Read configuration
    config = read_yaml("../config.yaml")

    my_ip, my_port = config["sender_ip"], config["port"]["acknowledgement"]["target"]
    remote_ip, remote_port = config["receiver_ip"], config["port"]["data"]["source"]

    file_name = config["file_name"]["sender"]
    chunk_size = MAX_DATA_SIZE - 4
    timeout = config["timeout"]

    # Read the whole file as bytes
    with open(file_name, "rb") as file:
        file_bytes = file.read(-1)

    # We must send the number of chunks to the server,
    # so that they know how many messages to receive
    chunks_count = ceil(len(file_bytes) / chunk_size)
    md5 = hashlib.md5(file_bytes).digest()

    chunks = {}
    for chunk_index in range(chunks_count):
        chunks[chunk_index] = file_bytes[chunk_index * chunk_size: (chunk_index + 1) * chunk_size]

    with Connection(my_ip, my_port, remote_ip, remote_port, timeout) as connection:
        while True:
            log("Starting send")

            # await that the connection is ok
            while not connection.remote_status == b"receive ready":
                time.sleep(0.1)

            log("Receiver ready")
            connection.status = b"begin send"

            # send header
            log("Sending header")
            while not connection.remote_status == b"header received":
                connection.send_message(b"header", struct.pack("i", chunks_count) + md5)

            for chunk_index in range(WINDOW_SIZE):
                chunk = struct.pack("i", chunk_index) + chunks[chunk_index]
                connection.send_message(b"packet", chunk)

            # send data by chunks
            for chunk_index in chunks:
                log(f"Sending chunk {chunk_index + 1}/{chunks_count}")

                status = connection.remote_status
                while status != b"received " + struct.pack("i", chunk_index) and \
                        status != b"md5 ok" and status != b"md5 error":
                    connection.status = b"packet " + struct.pack("i", chunk_index)
                    chunk = struct.pack("i", chunk_index) + chunks[chunk_index]
                    connection.send_message(b"packet", chunk)
                    status = connection.remote_status

            # check md5
            log("Checking MD5")
            while True:
                if status == b"md5 ok":
                    log.success("Send successful")
                    exit(0)

                if status == b"md5 error":
                    log.error("MD5 mismatch")
                    break

            # Reset the receiver
            while not connection.remote_status == b"header received":
                connection.send_message(b"reset", b"")
