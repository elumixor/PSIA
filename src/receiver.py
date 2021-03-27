import hashlib
import struct

from connection import Connection
from utils import read_yaml

if __name__ == '__main__':
    # Read configuration
    config = read_yaml("../config.yaml")

    my_ip, my_port = config["receiver_ip"], config["port"]["data"]["target"]
    remote_ip, remote_port = config["sender_ip"], config["port"]["acknowledgement"]["source"]

    file_name = config["file_name"]["receiver"]
    chunk_size = config["chunk_size"]
    timeout = config["timeout"]
    attempts = config["attempts"]

    total_attempts = config["total_attempts"]

    with Connection(my_ip, my_port, remote_ip, remote_port, timeout, attempts) as connection:
        for attempt in range(total_attempts):
            try:
                # Receive the number of packets to receive
                chunks_count_bytes = connection.receive(4, timeout=False)
                chunks_count, = struct.unpack("i", chunks_count_bytes)

                # Receive the hash for the whole file
                file_md5_key = connection.receive(16)

                file_bytes = b""

                # Receive image by chunks
                for i in range(chunks_count):
                    data = connection.receive(chunk_size)
                    file_bytes += data

                if file_md5_key == hashlib.md5(file_bytes).digest():
                    print("File received successfully.")
                    connection.send_ok()
                    break

                print("MD5 do not match")
                connection.send_fail()

            except RuntimeError as e:
                print(e)

            print(f"Attempt {attempt} failed")

    # Write all bytes to a file
    with open(file_name, "wb") as file:
        file.write(file_bytes)
