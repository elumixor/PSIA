import hashlib
import struct

from receiver import Receiver

port = 5300
ip = "127.0.0.1"
packet_size = 1024
max_receive_attempts = 10
max_attempts = 10
timeout = 1
file_name = "received.jpg"

if __name__ == '__main__':
    with Receiver(ip, port, max_receive_attempts, timeout, verbose=True) as receiver:
        while True:
            try:
                # Receive the number of packets to receive and the md5 key sent together as
                # to reduce broadcast errors maintenance
                file_md5_and_chunks_count_bytes = receiver.receive(20)
                file_md5_key = file_md5_and_chunks_count_bytes[:16]
                chunks_count_bytes = file_md5_and_chunks_count_bytes[16:]
                chunks_count, = struct.unpack("i", chunks_count_bytes)
                receiver.last_packet_number = -1
                break
            except RuntimeError as e:
                print(e)

        file_bytes = b""
        for i in range(chunks_count):
            try:
                # Receive image by chunks
                data = receiver.receive(packet_size)
                file_bytes += data
            except RuntimeError as e:
                print(e)

        if file_md5_key == hashlib.md5(file_bytes).digest():
            print("File received successfully.")
            receiver.send_ok(struct.pack("i", 9999))
        else:
            print("MD5 do not match")

    # Write all bytes to a file
    with open(file_name, "wb") as file:
        file.write(file_bytes)
