import hashlib
import struct

from receiver import Receiver

port = 5300
ip = "127.0.0.1"
packet_size = 1020
max_receive_attempts = 10
max_attempts = 10
file_name = "data/received.jpg"

if __name__ == '__main__':
    with Receiver(ip, port, max_receive_attempts, verbose=True) as receiver:
        for attempt in range(max_attempts):
            try:
                # Receive the number of packets to receive
                chunks_count_bytes = receiver.receive(4)
                chunks_count, = struct.unpack("i", chunks_count_bytes)

                # Receive the hash for the whole file
                file_md5_key = receiver.receive(16)

                file_bytes = b""

                # Receive image by chunks
                for i in range(chunks_count):
                    data = receiver.receive(packet_size)
                    file_bytes += data

                if file_md5_key == hashlib.md5(file_bytes).digest():
                    print("File received successfully.")
                    receiver.send_ok()
                    break

                print("MD5 do not match")
                receiver.send_fail()

            except RuntimeError as e:
                print(e)

            print(f"Attempt {attempt} failed")

    # Write all bytes to a file
    with open(file_name, "wb") as file:
        file.write(file_bytes)
