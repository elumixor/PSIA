import socket

port = 5300
ip = "127.0.0.1"

if __name__ == '__main__':
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    message = b"Hello world"  # send as bytes
    client_socket.sendto(message, (ip, port))

    # Receive response
    data, server = client_socket.recvfrom(1024)

    print(f"Received {data} from {server}")
