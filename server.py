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
pack_seq_num = '!I'
minimum_payload_size = 1200
padding_sequence_len = 1200-seq_len
padding_sequence = ('A'*padding_sequence_len).encode()
inf = float('inf')

parser = argparse.ArgumentParser()
parser.add_argument('-p', '--port', default=13579)
args = parser.parse_args()
ports = [args.port, args.port+1]

for port in ports:
  sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
  sock.bind(('::', port))
  socks.append(sock)
  send_times.append({})
  seq_nums.append(0)

main_socket = socks[0]

# Just get an estimate of the RTT
data, addr = socks[0].recvfrom(1500)
initial_addr = addr
t1 = time.time()
ret_msg = struct.pack(pack_seq_num, 0)
main_socket.sendto(ret_msg, addr)
data, addr = socks[0].recvfrom(1500)
initial_rtt = time.time() - t1

# Detection part starting
already_encountered_loss = False
rates = [15, 30]
latest_rtts = [initial_rtt] * len(ports)
unpack_ack_and_sock_index = '!IB'
recv_packet_len = seq_len + from_socket_len
for sock in socks:
  sock.setblocking(False)
next_socket = 0
port_indices = range(len(ports))
data_buffer = bytearray(recv_packet_len)
send_buffer = bytearray(minimum_payload_size)
very_beginning = time.time()
for cycle_num in range(sys.maxsize):
  seq_nums_beginning = list(seq_nums)
  num_acked = [0] * len(ports) 
  first_ack_times = [None] * len(ports)
  last_ack_times = [None] * len(ports)
  start_time = time.time()
  send_end_time = None
  min_time = 1/rates[0]
  time_to_run = max(max(max(latest_rtts), 0.1), min_time)
  should_send = [item*time_to_run for item in rates]
  seq_nums_end = None
  rates_in_mbit = [round(item*8*minimum_payload_size/1000000, 1) for item in rates]
  # print(f'Start {cycle_num=},{rates=}:{rates_in_mbit},{time_to_run}')
  while True:
    current_time = time.time()
    if seq_nums_end is None and current_time > start_time + time_to_run:
      seq_nums_end = list(seq_nums)
      send_end_time = current_time
    try:
      while True:
        main_socket.recv_into(data_buffer)
        ack_num, sock_index = struct.unpack(unpack_ack_and_sock_index, data_buffer)
        latest_rtts[sock_index] = current_time - send_times[sock_index][ack_num]
        if ack_num >= seq_nums_beginning[sock_index] and (seq_nums_end is None or ack_num < seq_nums_end[sock_index]):
          if num_acked[sock_index] == 0:
            first_ack_times[sock_index] = current_time
          num_acked[sock_index] += 1
        elif last_ack_times[sock_index] is None and seq_nums_end is not None and ack_num >= seq_nums_end[sock_index]-1:
          last_ack_times[sock_index] = current_time
        del send_times[sock_index][ack_num]
    except OSError as e:
      pass
    if all([item is not None for item in last_ack_times]):
      break

    next_send_time_delta = inf
    for i in port_indices:
      packets_that_should_have_been_sent = math.floor(rates[i]*(current_time-start_time))
      packets_that_were_not_sent_but_should_have = packets_that_should_have_been_sent - (seq_nums[i] - seq_nums_beginning[i])
      if packets_that_were_not_sent_but_should_have <= 0:
          delta_till_next_packet = start_time + (packets_that_should_have_been_sent + 1)/rates[i] - current_time
      else:
        delta_till_next_packet = -packets_that_were_not_sent_but_should_have
      if delta_till_next_packet <= next_send_time_delta:
        next_socket = i
        next_send_time_delta = delta_till_next_packet

    if next_send_time_delta > 0:
      time.sleep(next_send_time_delta)
    ret_msg = struct.pack(pack_seq_num, seq_nums[next_socket])
    send_buffer[:seq_len] = ret_msg
    socks[next_socket].sendto(send_buffer, addr)
    send_times[next_socket][seq_nums[next_socket]] = time.time()
    seq_nums[next_socket] += 1
  packets_actually_sent = [seq_nums_end_i-seq_nums_beginning_i for seq_nums_beginning_i, seq_nums_end_i in zip(seq_nums_beginning, seq_nums_end)]
  sent_enough = [math.ceil(packets_actually_sent_i) + 1 >= should_send_i * 15/16 for should_send_i, packets_actually_sent_i in zip(should_send, packets_actually_sent)]
  rtts_ms = [round(item*1000) for item in latest_rtts]
  first_ratio = ((num_acked[0]/(last_ack_times[0]-first_ack_times[0]))/
            (packets_actually_sent[0]/(send_end_time-start_time)))
  second_ratio = ((num_acked[1]/(last_ack_times[1]-first_ack_times[1]))/
            (packets_actually_sent[1]/(send_end_time-start_time)))
  # print(f'End {cycle_num=},{packets_actually_sent=},{rtts_ms=},{sent_enough=},{seq_nums_beginning=},{should_send=},{seq_nums_end=},{num_acked=},{seq_nums=},{first_ratio=},{second_ratio=}')
  
  if second_ratio < 0.5:
    loss_ratio = first_ratio/second_ratio
    # print('send_time_diff', send_end_time-start_time, 'ack_time_diff', [last-first for first, last in zip(first_ack_times, last_ack_times)], 
    #       'first_ack_diff', first_ack_times[0]-first_ack_times[1], 'last_ack_diff', last_ack_times[0]-last_ack_times[1])
    # print('recv_rate0', num_acked[0]/(last_ack_times[0]-first_ack_times[0]), 'send_rate0', (packets_actually_sent[0]/(send_end_time-start_time)),
    #       'recv_rate1', num_acked[1]/(last_ack_times[1]-first_ack_times[1]), 'send_rate1', (packets_actually_sent[1]/(send_end_time-start_time)))
    if loss_ratio >= 1.5:
      confidence = min((loss_ratio-1.5)*2, 1)
      print(f'Fair queuing detected with a confidence of {round(confidence*100)}%, {loss_ratio=}')
    else:
      confidence = min(1-((loss_ratio-1)*2), 1)
      print(f'First-come first-served detected with a confidence of {round(confidence*100)}%, {loss_ratio=}')
    break
  elif not all(sent_enough):
    print('Failed to utilize the link. Aborting')
    break
  rates = [rate*2 for rate in rates]

print('Terminating server')
main_socket.sendto(struct.pack('!I', 2**32 - 1), initial_addr)