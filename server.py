import math
import socket
from common import *
import time
import sys

socks = []
seq_nums = []
send_times = []
remote_addresses = [None] * 2

for port in ports:
  sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  sock.bind(('0.0.0.0', port))
  socks.append(sock)
  send_times.append({})
  seq_nums.append(0)

main_socket = socks[0]

def send_and_receive_acks(initial_rtt):
  rates = [15, 30]
  latest_rtts = [initial_rtt] * len(ports)
  main_socket.setblocking(False)
  for cycle_num in range(sys.maxsize):
    seq_nums_beginning = list(seq_nums)
    num_acked = [0] * len(ports) 
    start_time = time.time()
    time_to_run = max(max(latest_rtts), 0.1)
    should_send = [item*time_to_run for item in rates]
    seq_nums_end = None
    print(f'Start {cycle_num=},{rates=},{time_to_run}')
    while True:
      current_time = time.time()
      if current_time > start_time + 4*time_to_run:
        break
      elif seq_nums_end is None and current_time > start_time + time_to_run:
        seq_nums_end = list(seq_nums)
        # print(f'End first cycle {seq_nums_end}')
      try:
        while True:
          data, _ = main_socket.recvfrom(8)
          assert len(data) == seq_len + from_socket_len, f'{data}'
          ack_num, sock_index = struct.unpack('!IB', data[0:5])
          latest_rtts[sock_index] = current_time - send_times[sock_index][ack_num]
          if seq_nums_end is None or ack_num < seq_nums_end[sock_index]:
            num_acked[sock_index] += 1
          del send_times[sock_index][ack_num]
      except OSError as e:
        pass
      
      next_send_time_delta = inf
      next_socket = 0
      for i in range(len(ports)-1, -1, -1):
        packets_that_should_have_been_sent = math.floor(rates[i]*(current_time-start_time))
        if packets_that_should_have_been_sent < seq_nums[i] - seq_nums_beginning[i]:
            delta_till_next_packet = start_time + (packets_that_should_have_been_sent + 1)/rates[i] - current_time
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
      send_times[next_socket][seq_nums[next_socket]] = time.time()
      seq_nums[next_socket] += 1
    sent_enough = [math.ceil(num_acked_i) + 1 >= should_send_i * 7/8 for should_send_i, num_acked_i in zip(should_send, num_acked)]
    print(f'End {cycle_num=},{latest_rtts=},{sent_enough=},{seq_nums_beginning=},{should_send=},{seq_nums_end=},{num_acked=},{seq_nums=}')
    if not all(sent_enough):
      print('Failed to utilize the link. Aborting.')
      return
    else: 
      rates = [rate*2 for rate in rates]
data, addr = socks[0].recvfrom(minimum_payload_size)
t1 = time.time()
ret_msg = struct.pack('!I', 0)
main_socket.sendto(ret_msg, addr)
data, addr = socks[0].recvfrom(minimum_payload_size)
initial_rtt = time.time() - t1
print(f'{initial_rtt=}')

send_and_receive_acks(initial_rtt)
