import math
import socket
from select import select
from common import *
import time

socks = []
seq_nums = []
send_times = []
remote_addresses = [None] * 2
packets_to_send = [10000, 20000]
time_to_run = 1

for port in ports:
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
  while True:
    current_time = time.time()
    # if last_rtt is not None and current_time > start_time + last_rtt:
    if last_rtt is not None and current_time > start_time + time_to_run:
        break
    try:
      while True:
        data, _ = socks[0].recvfrom(100)
        ack_num, sock_index = struct.unpack('!IB', data[0:5])
        last_rtt = current_time - send_times[sock_index][ack_num]
        del send_times[sock_index][ack_num]
    except:
      pass

    next_send_time_delta = inf
    next_socket = 0
    for i in range(len(ports)):
      packets_that_should_have_been_sent = math.floor(packets_to_send[i]/((current_time-start_time)/time_to_run))
      if packets_that_should_have_been_sent >= seq_nums[i]:
          next_send_time_delta = (packets_to_send[i]/time_to_run)*(current_time-start_time)
          delta_till_next_packet = (time_to_run/packets_to_send[i]) * (packets_that_should_have_been_sent + 1) - current_time
          if delta_till_next_packet < next_send_time_delta:
            next_socket = i
            next_send_time_delta = delta_till_next_packet

    if next_send_time_delta < inf:
      time.sleep(next_send_time_delta)
    ret_msg = struct.pack('!I', seq_nums[next_socket]) + \
        padding_sequence
    socks[next_socket].sendto(ret_msg, addr)
    send_times[next_socket][seq_nums[next_socket]] = current_time
    seq_nums[next_socket] += 1
  print(f'{last_rtt=},{seq_nums=}')
        
data, addr = socks[0].recvfrom(minimum_payload_size)

send_and_receive_acks()
