import socket
from select import select
from common import *

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
msg = packed_zero + \
    packed_zero

sock.sendto(msg, ("127.0.0.1", udp_ports[0]))

while True:
    data, addr = sock.recvfrom(minimum_payload_size)
    msg = packed_zero + data[:4]
    sock.sendto(msg, addr)
