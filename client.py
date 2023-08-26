import socket
from select import select
from common import *

socks = []
for i, port in enumerate(udp_ports):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    socks.append(sock)
    msg = packed_zero + \
        packed_zero

    sock.sendto(msg, ("127.0.0.1", udp_ports[i]))

while True:
    ready_socks,_,_ = select(socks, [], []) 
    for sock in ready_socks:
        data, addr = sock.recvfrom(minimum_payload_size)
        msg = packed_zero + data[:4]
        sock.sendto(msg, addr)
