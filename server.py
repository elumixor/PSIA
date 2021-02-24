import socket

port = 5300
ip = "127.0.0.1"
SIZE = 1024

if __name__ == '__main__':
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((ip, port))

    file = open('received.jpg', 'wb')
    message, address = server_socket.recvfrom(SIZE)
    while message:
        file.write(message)
        message, address = server_socket.recvfrom(SIZE)

    file.close()
    server_socket.close()