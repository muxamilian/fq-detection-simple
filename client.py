import socket
import select
from common import *

socks = []
seq_nums = []
for i, port in enumerate(udp_ports):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    socks.append(sock)
    seq_nums.append(0)
    sock.sendto(generate_message(seq_nums[i], 0), ("127.0.0.1", udp_ports[i]))

# while True:
for _ in range(2):
    ready_socks,_,_ = select.select(socks, [], []) 
    for sock in ready_socks:
        data, addr = sock.recvfrom(minimum_payload_size)
        recv_seq_num, recv_ack_num = decode_message(data)
        s_i = socks.index(sock)
        print(f'client received on sock {s_i} with {recv_seq_num=}, {recv_ack_num=}')
