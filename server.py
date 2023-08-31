#!/usr/bin/python
import argparse
import math
import socket
import time
import sys
import struct

socks = []
seq_nums = []
send_times = []
remote_addresses = [None] * 2
seq_len = 4
from_socket_len = 1
minimum_payload_size = 1200
padding_sequence_len = 1200-seq_len-from_socket_len
padding_sequence = ('A'*padding_sequence_len).encode()
inf = float('inf')

parser = argparse.ArgumentParser()
parser.add_argument('-p', '--port', default=13579)
args = parser.parse_args()
ports = [args.port, args.port+1]

for port in ports:
  sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  sock.bind(('0.0.0.0', port))
  socks.append(sock)
  send_times.append({})
  seq_nums.append(0)

main_socket = socks[0]

# Just get an estimate of the RTT
data, addr = socks[0].recvfrom(1500)
initial_addr = addr
t1 = time.time()
ret_msg = struct.pack('!I', 0)
main_socket.sendto(ret_msg, addr)
data, addr = socks[0].recvfrom(1500)
initial_rtt = time.time() - t1
print(f'{initial_rtt=}')

# Detection part starting
already_encountered_loss = False
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
    try:
      while True:
        data, _ = main_socket.recvfrom(8)
        assert len(data) == seq_len + from_socket_len, f'{data}'
        ack_num, sock_index = struct.unpack('!IB', data[0:5])
        latest_rtts[sock_index] = current_time - send_times[sock_index][ack_num]
        if ack_num >= seq_nums_beginning[sock_index] and (seq_nums_end is None or ack_num < seq_nums_end[sock_index]):
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
      else:
        delta_till_next_packet = 0
      if delta_till_next_packet <= next_send_time_delta:
        next_socket = i
        next_send_time_delta = delta_till_next_packet

    if next_send_time_delta > 0:
      time.sleep(next_send_time_delta)
    ret_msg = struct.pack('!I', seq_nums[next_socket]) + \
        padding_sequence
    socks[next_socket].sendto(ret_msg, addr)
    send_times[next_socket][seq_nums[next_socket]] = time.time()
    seq_nums[next_socket] += 1
  packets_actually_sent = [seq_nums_end_i-seq_nums_beginning_i for seq_nums_beginning_i, seq_nums_end_i in zip(seq_nums_beginning, seq_nums_end)]
  sent_enough = [math.ceil(packets_actually_sent_i) + 1 >= should_send_i * 7/8 for should_send_i, packets_actually_sent_i in zip(should_send, packets_actually_sent)]
  print(f'End {cycle_num=},{packets_actually_sent=},{latest_rtts=},{sent_enough=},{seq_nums_beginning=},{should_send=},{seq_nums_end=},{num_acked=},{seq_nums=}')
  
  if not all(sent_enough):
    print('Failed to utilize the link. Aborting.')
    break
  # elif num_acked[0] < packets_actually_sent[0]:
  #   print('Had packet loss on the flow sending less. That shouldn\'t happen. Aborting.')
  #   quit(1)
  elif num_acked[1] < packets_actually_sent[1] * 7/8:
    if not already_encountered_loss:
      already_encountered_loss = True
      acked_over_sent = num_acked[1]/packets_actually_sent[1]
      print(f'Encountered packet loss, {acked_over_sent=}')
      rates = [rate*acked_over_sent*2 for rate in rates]
    else:
      loss_ratio = (num_acked[0]/packets_actually_sent[0])/(num_acked[1]/packets_actually_sent[1])
      if loss_ratio >= 1.5:
        confidence = (loss_ratio-1.5)*2
        print(f'Fair queuing detected with a confidence of {round(confidence*100)}%')
      else:
        confidence = 1-((loss_ratio-1)*2)
        print(f'Fair queuing NOT detected with a confidence of {round(confidence*100)}%')
      break
  else: 
    rates = [rate*2 for rate in rates]

main_socket.sendto(struct.pack('!I', 2**32 - 1), initial_addr)