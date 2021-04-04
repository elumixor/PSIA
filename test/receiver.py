import hashlib
import struct
import sys
import time
import socket
import zlib

from utils import read_yaml, log
from sender import WINDOW_SIZE, MAX_DATA_SIZE

if __name__ == "__main__":
    # Read configuration
    config = read_yaml("../config.yaml")

    my_ip, my_port = config["sender_ip"], config["port"]["data"]["target"] # 5301
    remote_ip, remote_port = config["receiver_ip"], config["port"]["acknowledgement"]["source"] # 5100

    file_name = config["file_name"]["receiver"]
    chunk_size = MAX_DATA_SIZE
    timeout = config["timeout"]

    send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    send_socket.settimeout(timeout)

    receive_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    receive_socket.bind(("", my_port))
    receive_socket.settimeout(1)

    chunk_count = 0
    # receive header
    while True:
        try:
            data, _ = receive_socket.recvfrom(24)
            chunk_count, = struct.unpack("i", data[:4])
            chunk_count_crc = data[4:8]
            md5 = data[8:]
            if chunk_count_crc == struct.pack("I", zlib.crc32(data[:4])):
                send_socket.sendto(struct.pack("i", 1), (remote_ip, remote_port))
                break
            else:
                send_socket.sendto(struct.pack("i", 0), (remote_ip, remote_port))

        except socket.timeout:
            ...
    log.info("header received")

    chunks = {}
    chunk_index_list = [x for x in range(1, chunk_count + 1)]
    chunk_missing_list = []

    # receive data
    received_packets = 0
    while received_packets < chunk_count:

        chunk_index_list = sorted(list(set(chunk_missing_list + chunk_index_list)))
        print("still waiting for", chunk_index_list)
        window = WINDOW_SIZE if len(chunk_index_list) > WINDOW_SIZE else len(chunk_index_list)
        for _ in range(window):
            expected_packet_index = chunk_index_list[0]
            try:
                data, _ = receive_socket.recvfrom(1024)
                chunk_index, = struct.unpack("i", data[:4])
                chunk = data[4:-4]
                crc = data[-4:]
                if crc == struct.pack("I", zlib.crc32(data[:-4])) and expected_packet_index == chunk_index:
                    log.success("received", chunk_index)
                    chunks[chunk_index] = chunk
                    received_packets += 1
                    chunk_index_list.remove(chunk_index)
                    if chunk_index in chunk_missing_list:
                        chunk_missing_list.remove(chunk_index)
                elif crc == struct.pack("I", zlib.crc32(data[:-4])):
                    log.success("expected", expected_packet_index, "got", chunk_index)
                    if chunk_index in chunk_index_list:
                        chunks[chunk_index] = chunk
                        received_packets += 1
                        chunk_index_list.remove(chunk_index)
                    # chunk_missing_list.append(expected_packet_index)
                    # chunk_index_list.pop(0)
                else:
                    log.error("chunk", chunk_index, "corrupted")
                    chunk_missing_list.append(expected_packet_index)
                    if expected_packet_index in chunk_index_list:
                        chunk_index_list.remove(expected_packet_index)
            except socket.timeout:
                log.error("chunk index", expected_packet_index, "timeout")
                chunk_missing_list.append(expected_packet_index)
                chunk_index_list.pop(0)

        # sending request for missing packets
        chunk_missing_list = list(set(chunk_missing_list))
        log.info("missing packets list",chunk_missing_list)
        missing_index_packet = b""
        for missing_index in chunk_missing_list:
            missing_index_packet += struct.pack("i", missing_index)
        missing_index_packet += b"\0" * (WINDOW_SIZE * 4 - len(missing_index_packet))
        send_socket.sendto(missing_index_packet + struct.pack("I", zlib.crc32(missing_index_packet)), (remote_ip, remote_port))
        print("-----------")

    log.info("writing to file")
    # write to file
    file_bytes = b""
    for chunk_index in sorted(chunks.keys()):
        # print(chunk_index, len(chunks[chunk_index]), chunks[chunk_index])
        file_bytes += chunks[chunk_index]

    if hashlib.md5(file_bytes).digest() == md5:
        log.success("md5 keys match")
        with open(file_name, "wb") as file:
            file.write(file_bytes)
    else:
        log.error("md5 keys do not match")
