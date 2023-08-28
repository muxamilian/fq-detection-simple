import math
import socket
from select import select
from common import *
import time

socks = []
seq_nums = []
send_times = []
remote_addresses = [None] * 2
packets_to_send = [5000, 10000]
time_to_run = 1

for port in ports:
  sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  sock.bind(('0.0.0.0', port))
  socks.append(sock)
  send_times.append({})
  seq_nums.append(0)

main_socket = socks[0]

def send_and_receive_acks():
  main_socket.setblocking(False)
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
        data, _ = main_socket.recvfrom(8)
        assert len(data) == seq_len
        ack_num, sock_index = struct.unpack('!IB', data[0:5])
        last_rtt = current_time - send_times[sock_index][ack_num]
        del send_times[sock_index][ack_num]
    except:
      pass
    
    next_send_time_delta = inf
    next_socket = 0
    for i in range(len(ports)-1, -1, -1):
      packets_that_should_have_been_sent = math.floor(packets_to_send[i]*((current_time-start_time)/time_to_run))
      if packets_that_should_have_been_sent < seq_nums[i]:
          delta_till_next_packet = start_time + (time_to_run/packets_to_send[i]) * (packets_that_should_have_been_sent + 1) - current_time
          assert delta_till_next_packet >= 0, f'{packets_that_should_have_been_sent=},{seq_nums[i]},{delta_till_next_packet=}'
          # print(f'{i=}, {packets_that_should_have_been_sent=}, {seq_nums[i]=}, {delta_till_next_packet=}')
      else:
        delta_till_next_packet = 0
      if delta_till_next_packet <= next_send_time_delta:
        next_socket = i
        next_send_time_delta = delta_till_next_packet

    # print(f'sleeping for {next_send_time_delta=}, sending on {next_socket}')
    if 0 < next_send_time_delta:
      time.sleep(next_send_time_delta)
    ret_msg = struct.pack('!I', seq_nums[next_socket]) + \
        padding_sequence
    socks[next_socket].sendto(ret_msg, addr)
    send_times[next_socket][seq_nums[next_socket]] = current_time
    seq_nums[next_socket] += 1
  print(f'{last_rtt=},{seq_nums=}')

data, addr = socks[0].recvfrom(minimum_payload_size)

send_and_receive_acks()
