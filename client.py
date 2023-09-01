#!/usr/bin/python
import argparse
import socket
import struct

parser = argparse.ArgumentParser()
parser.add_argument('-p', '--port', default=13579)
parser.add_argument('-s', '--server-ip-address', default='127.0.0.1')
args = parser.parse_args()
ports = [args.port, args.port+1]
minimum_payload_size = 1200
packet_seq_num = '!I'
pack_byte = 'B'
seq_num_len = 4

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
base_addr = (args.server_ip_address, ports[0])

sock.sendto(struct.pack(packet_seq_num, 0), base_addr)
print('client sent handshake to server')

# Just echo everything back forever
while True:
    data, addr = sock.recvfrom(seq_num_len)
    msg = data
    seq_num = struct.unpack(packet_seq_num, msg)[0]
    if seq_num == 2**32 - 1:
        break
    sock.sendto(msg + struct.pack(pack_byte, ports.index(addr[1])), base_addr)
