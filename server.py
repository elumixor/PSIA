import socket

port = 5300
ip = ""

if __name__ == '__main__':
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((ip, port))

    message, address = server_socket.recvfrom(1024)
    print(f"Received: {message} from {address}")

    # Reply
    server_socket.sendto(message, address)
