import socket
import struct
import zlib
import hashlib

port = 5300
ip = "127.0.0.1"
packet_size = 1024

if __name__ == '__main__':
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as socket:
        socket.bind((ip, port))

        # Receive the number of chunks (messages) to receive later
        chunks_count_bytes, address = socket.recvfrom(4)  # sizeof int = 4
        chunks_count = struct.unpack("i", chunks_count_bytes)[0]  # byte array -> int

        file_bytes = b""
        chunk_md5_key = hashlib.md5()

        # Receive image by chunks
        for _ in range(chunks_count):
            while True:
                message, _ = socket.recvfrom(packet_size)
                rec_chunk_crc32 = struct.unpack("I", message[-4:])[0]
                data = message[:-4]
                if rec_chunk_crc32 != zlib.crc32(data):
                    print("Crc32 keys do not match. Requesting resend.")
                    socket.sendto(struct.pack("?", False), address)
                else:
                    file_bytes += data
                    socket.sendto(struct.pack("?", True), address)
                    chunk_md5_key.update(data)
                    break

        file_md5_key = hashlib.md5(file_bytes)
        if file_md5_key.digest() == chunk_md5_key.digest():
            print("File received successfully.")
        else:
            print("Error: files do not match.")

    # Write all bytes to a file
    with open('received.jpg', 'wb') as file:
        file.write(file_bytes)

