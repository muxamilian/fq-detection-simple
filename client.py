#!/usr/bin/python
import argparse
import socket
import struct

parser = argparse.ArgumentParser()
parser.add_argument('-p', '--port', default=13579)
args = parser.parse_args()
ports = [args.port, args.port+1]
minimum_payload_size = 1200

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
base_addr = ("127.0.0.1", ports[0])

sock.sendto(struct.pack('!I', 0), base_addr)
print('client sent handshake to server')

# Just echo everything back forever
while True:
    data, addr = sock.recvfrom(minimum_payload_size)
    msg = data[:4]
    seq_num = struct.unpack('!I', msg)[0]
    if seq_num == 2**32 - 1:
        break
    sock.sendto(msg + struct.pack('B', ports.index(addr[1])), base_addr)
