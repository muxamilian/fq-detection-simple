#!/usr/bin/python
import argparse
import socket
import struct
from select import select 

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
final_seq_num = 2**32 - 1

# Just echo everything back forever
while True:
    readable, _, _ = select([sock], [], [], 5)
    if len(readable) == 0:
        print('Timeout in client')
        break
    data, addr = readable[0].recvfrom(seq_num_len, 5)
    seq_num = struct.unpack(packet_seq_num, data)[0]
    sock_num = ports.index(addr[1])
    if seq_num == final_seq_num:
        print('Terminating client')
        break
    sock.sendto(data + struct.pack(pack_byte, sock_num), base_addr)
