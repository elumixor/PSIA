chunk_size = 1016

with open("../data/original.jpg", "rb") as file:
    content = file.read()
    for i in range(1, 32 + 1):
        packet = content[(i - 1) * chunk_size: i * chunk_size]
        print(i, len(packet), packet)

with open("../data/received.jpg", "wb") as file:
    file.write(content)