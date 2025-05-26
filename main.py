from socket import socket, AF_INET, SOCK_DGRAM

server = socket(AF_INET, SOCK_DGRAM)
server.bind(('localhost', 8080))
server.listen(1)
conn, addr = server.accept()
while (x := int(input()) != 0):

conn.close()
