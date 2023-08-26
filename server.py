import socket
import select
from common import *

socks = []
seq_nums = []
for port in udp_ports:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    socks.append(sock)
    seq_nums.append(0)
    sock.bind(('0.0.0.0', port))

# while True:
for _ in range(2):
    ready_socks,_,_ = select.select(socks, [], []) 
    for sock in ready_socks:
        data, addr = sock.recvfrom(minimum_payload_size)
        recv_seq_num, recv_ack_num = decode_message(data)
        s_i = socks.index(sock)
        print(f'server received on sock {s_i} with {recv_seq_num=}, {recv_ack_num=}')
        sock.sendto(generate_message(seq_nums[s_i], recv_seq_num), addr)

