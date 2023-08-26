import socket
from select import select
from common import *
import time

socks = []
seq_nums = []
send_times = []
remote_addresses = [None] * 2
for port in udp_ports:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    socks.append(sock)
    send_times.append({})
    seq_nums.append(0)
    sock.bind(('0.0.0.0', port))

def send_and_receive_acks():
    socks[0].setblocking(False)
    # last_rtt = None
    last_rtt = 1
    start_time = time.time()
    last_sent = 0
    while True:
        current_time = time.time()
        # if last_rtt is not None and current_time > start_time + last_rtt:
        if last_rtt is not None and current_time > start_time + 10:
            break
        # r,_,_ = select([socks[0]],[],[],0)
        # for sock in r:
        try:
            data, _ = socks[0].recvfrom(8)
            ack_num = struct.unpack('!I', data[4:8])[0]
            # sock_index = socks.index(sock)
            # last_rtt = current_time - send_times[sock_index][ack_num]
            # del send_times[sock_index][ack_num]
        except:
            pass

        ret_msg = struct.pack('!I', seq_nums[last_sent]) + \
            packed_zero + \
            padding_sequence
        socks[last_sent].sendto(ret_msg, addr)
        # send_times[last_sent][seq_nums[last_sent]] = current_time
        seq_nums[last_sent] += 1
        last_sent = (last_sent + 1) % 2
    print(f'{last_rtt=},{seq_nums=}')
        
data, addr = socks[0].recvfrom(minimum_payload_size)

send_and_receive_acks()
