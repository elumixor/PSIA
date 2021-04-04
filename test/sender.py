import hashlib
import struct
import time
from math import ceil
import zlib
import socket

from utils import read_yaml, log

WINDOW_SIZE = 4

INDEX_SIZE = 4
MAX_PACKET_SIZE = 1024
CRC_SIZE = 4
MAX_DATA_SIZE = MAX_PACKET_SIZE - INDEX_SIZE - CRC_SIZE

if __name__ == "__main__":
    # Read configuration
    config = read_yaml("../config.yaml")

    my_ip, my_port = config["sender_ip"], config["port"]["acknowledgement"]["target"] #5101
    remote_ip, remote_port = config["receiver_ip"], config["port"]["data"]["source"] # 5300

    file_name = config["file_name"]["sender"]
    chunk_size = MAX_DATA_SIZE
    timeout = config["timeout"]

    send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    send_socket.settimeout(timeout)

    receive_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    receive_socket.bind(("", my_port))
    receive_socket.settimeout(1)  # set a small timeout on the receive socket

    # Read the whole file as bytes
    with open(file_name, "rb") as file:
        file_bytes = file.read(-1)

    # We must send the number of chunks to the server,
    # so that they know how many messages to receive
    chunks_count = ceil(len(file_bytes) / chunk_size)
    md5 = hashlib.md5(file_bytes).digest()

    # sending header
    while True:
        try:
            packet = struct.pack("i", chunks_count) + md5
            crc = struct.pack("I", zlib.crc32(packet))
            send_socket.sendto(packet + crc, (remote_ip, remote_port))
            ack, _ = receive_socket.recvfrom(4)
            if ack == struct.pack("i", 1):
                break
        except socket.timeout:
            ...

    log.info("Header send")

    # storing chunks in a dictionary
    chunks = {}
    for chunk_index in range(1, chunks_count + 1):
        chunks[chunk_index] = file_bytes[(chunk_index - 1) * chunk_size: chunk_index * chunk_size]

    chunk_index_list = [x for x in range(1, chunks_count + 1)]

    # sending chunks
    while len(chunk_index_list) != 0:
        # send N packets
        window = WINDOW_SIZE if len(chunk_index_list) > WINDOW_SIZE else len(chunk_index_list)
        current_window = sorted(chunk_index_list[:window])
        log.info("current window", current_window)

        for index in current_window:
            #chunk_index = index
            # log(f"Sending chunk {chunk_index + 1}/{chunks_count}")
            log.info("now sending packet", index)
            packet = struct.pack("i", index) + chunks[index]
            crc = struct.pack("I", zlib.crc32(packet))
            send_socket.sendto(packet + crc, (remote_ip, remote_port))
            time.sleep(0.3)

        try:
            missing_packets = []
            missing_packet_bytes, _ = receive_socket.recvfrom(WINDOW_SIZE * 4 + 4)
            crc = missing_packet_bytes[-4:]
            missing_packet_bytes = missing_packet_bytes[:-4]

            if crc != struct.pack("I", zlib.crc32(missing_packet_bytes)):
                log.error("ack corrupted")
                continue

            for i in range(WINDOW_SIZE):
                missing_packet = missing_packet_bytes[i * 4: (i+1) * 4]
                missing_packet, = struct.unpack("i", missing_packet)
                if missing_packet != 0:
                    missing_packets.append(missing_packet)

            log.error("packets to resend", missing_packets)
            for index in current_window:
                if index not in missing_packets:
                    chunk_index_list.remove(index)

        except socket.timeout:
            log.error("ack timeout")

