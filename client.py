import socket
import struct
from math import ceil

port = 5300
ip = "127.0.0.1"
chunk_size = 1024
input_file = "original.jpg"

if __name__ == '__main__':
    # Read the whole file as bytes
    with open(input_file, "rb") as file:
        file_bytes = file.read(-1)

    # We must send the number of chunks to the server,
    # so that they know how many messages to receive
    chunks_count = ceil(len(file_bytes) / chunk_size)

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client_socket:
        # Send the chunk size as a byte array
        client_socket.sendto(struct.pack("i", chunks_count), (ip, port))

        # Send bytes by chunks
        for i in range(chunks_count):
            chunk = file_bytes[i * chunk_size: (i + 1) * chunk_size]
            client_socket.sendto(chunk, (ip, port))
