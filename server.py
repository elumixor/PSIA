import socket
import struct

port = 5300
ip = "127.0.0.1"
chunk_size = 1024

if __name__ == '__main__':
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as socket:
        socket.bind((ip, port))

        # Receive the number of chunks (messages) to receive later
        chunks_count_bytes, address = socket.recvfrom(4)  # sizeof int = 4
        chunks_count = struct.unpack("i", chunks_count_bytes)[0]  # byte array -> int

        file_bytes = b""

        # Receive image by chunks
        for _ in range(chunks_count):
            message, _ = socket.recvfrom(chunk_size)
            file_bytes += message

    # Write all bytes to a file
    with open('received.jpg', 'wb') as file:
        file.write(file_bytes)
