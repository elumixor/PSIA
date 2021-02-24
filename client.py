import socket

port = 5300
ip = "127.0.0.1"
SIZE = 1024

if __name__ == '__main__':
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    file = open("original.jpg", "rb")
    message = file.read(SIZE)

    while message:
        client_socket.sendto(message, (ip, port))
        message = file.read(SIZE)

    file.close()
    client_socket.close()