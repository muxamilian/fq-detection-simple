#!/usr/bin/python
import argparse
import socket
import struct
from select import select 

# The client basically only echoes acknowledgements to the server
# The server code is more interesting
parser = argparse.ArgumentParser()
parser.add_argument('-p', '--port', default=13579)
parser.add_argument('-s', '--server-address', default='127.0.0.1')
parser.add_argument('--ipv6', action='store_true')
args = parser.parse_args()
ports = [args.port, args.port+1]
packet_seq_num = '!I'
pack_byte = 'B'
seq_num_len = 4
timestamp_len = 8
timeout = 5

if args.ipv6:
    address_family = socket.AF_INET6
else:
    address_family = socket.AF_INET
# Get IP address from host name
resolved_server_address = socket.getaddrinfo(args.server_address, args.port, address_family, socket.SOCK_DGRAM)
sock = socket.socket(address_family, socket.SOCK_DGRAM)
# Address of the server and port number
base_addr = (resolved_server_address[0][4][0], ports[0]+2)
send_sock = socket.socket(address_family, socket.SOCK_DGRAM)
send_sock.connect(base_addr)

# Send some kind of handshake
sock.sendto(struct.pack(packet_seq_num, 0), base_addr)

# Just echo everything back forever
while True:
    # Receive packet from server or timeout
    readable, _, _ = select([sock], [], [], timeout)
    if len(readable) == 0:
        print('Timeout in client')
        break
    data, addr = readable[0].recvfrom(seq_num_len + timestamp_len)
    sock_num = ports.index(addr[1])
    # Echo back and tell the server from port it came, the lower one or the higher one. 
    # This is encoded in `sock_num`
    send_sock.send(data + struct.pack(pack_byte, sock_num))
