import hashlib
import struct
from math import ceil

from sender import Sender

port = 5300
ip = "127.0.0.1"
chunk_size = 1016
file_name = "original.jpg"
max_packet_attempts = 10
max_attempts = 10
timeout = 1

if __name__ == '__main__':
    # Read the whole file as bytes
    with open(file_name, "rb") as file:
        file_bytes = file.read(-1)

    # We must send the number of chunks to the server,
    # so that they know how many messages to receive
    chunks_count = ceil(len(file_bytes) / chunk_size)

    with Sender(ip, port, max_packet_attempts, timeout, verbose=True) as sender:
        while True:
            try:
                # sends md5_key and the number of chunks together
                file_md5_key = hashlib.md5(file_bytes)
                chunks_count_bytes = struct.pack("i", chunks_count)
                sender.send(file_md5_key.digest() + chunks_count_bytes, 0)
                break
            except RuntimeError as e:
                print(e)

        for i in range(chunks_count):
            while True:
                chunk = file_bytes[i * chunk_size: (i + 1) * chunk_size]
                try:
                    sender.send(chunk, i)
                    break

                except RuntimeError as e:
                    print(e)

        if sender.send_succeeded:
            print("Send OK")
        else:
            print("Unexpected error. Repeat broadcast")

