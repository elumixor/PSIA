import hashlib
import struct
from math import ceil

from sender import Sender

port = 5300
ip = "127.0.0.1"
chunk_size = 1020
file_name = "data/original.jpg"
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
        for attempt in range(max_attempts):
            try:
                # Send the chunk size as a byte array
                sender.send(struct.pack("i", chunks_count))

                # Send the MD5 of the whole data
                file_md5_key = hashlib.md5(file_bytes)
                sender.send(file_md5_key.digest())

                # Send bytes by chunks
                for i in range(chunks_count):
                    chunk = file_bytes[i * chunk_size: (i + 1) * chunk_size]
                    sender.send(chunk)

                # Receive the confirmation for the whole file
                if sender.send_succeeded:
                    print("Send ok")
                    break

            except RuntimeError as e:
                print(e)

            print(f"Attempt {attempt} failed")
