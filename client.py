import socket
from select import select
from common import *

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
base_addr = ("127.0.0.1", ports[0])

sock.sendto(struct.pack('!I', 0), base_addr)
print('client sent handshake to server')

while True:
    data, addr = sock.recvfrom(minimum_payload_size)
    msg = data[:4]
    sock.sendto(msg + struct.pack('B', ports.index(addr[1])), base_addr)
