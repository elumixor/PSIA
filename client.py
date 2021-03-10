import socket
import struct
import zlib
from math import ceil

port = 5300
ip = "127.0.0.1"
chunk_size = 1020
input_file = "original.jpg"

if __name__ == '__main__':
    # Read the whole file as bytes
    with open(input_file, "rb") as file:
        file_bytes = file.read(-1)

    # We must send the number of chunks to the server,
    # so that they know how many messages to receive
    chunks_count = ceil(len(file_bytes) / chunk_size)

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0) as client_socket:
        client_socket.settimeout(2)
        # Send the chunk size as a byte array
        client_socket.sendto(struct.pack("i", chunks_count), (ip, port))

        # Send bytes by chunks
        for i in range(chunks_count):
            chunk = file_bytes[i * chunk_size: (i + 1) * chunk_size]
            chunk_crc32 = zlib.crc32(chunk)  # unsigned int
            message = chunk + struct.pack("I", chunk_crc32)
            while True:
                client_socket.sendto(message, (ip, port))

                # receiving confirmation
                confirmation, _ = client_socket.recvfrom(1)
                if confirmation == struct.pack("?", True):
                    break
