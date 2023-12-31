#!/usr/bin/python
import argparse
import math
import socket
import time
import sys
import struct
from typing import List

socks: List[socket.socket] = []
seq_nums = []
seq_len = 4
timestamp_len = 8
from_socket_len = 1
pack_seq_num_and_timestamp = '!Id'
unpack_ack_and_timestamp_and_sock_index = '!IdB'
inf = float('inf')

parser = argparse.ArgumentParser()
parser.add_argument('-p', '--port', default=13579)
parser.add_argument('--mtu', type=int, default=1500)
parser.add_argument('--debug', action='store_true')
args = parser.parse_args()
# Two ports are used. The second port sends with twice the bandwidth. 
# If there's fair queuing, one will see that more data is sent from the second flow, 
# but because of fair queuing, the client receives the same bandwidth from both flows. 
ports = [args.port, args.port+1]

# Subtract 40 for IPv6 and 8 for UDP
payload_size = args.mtu - 40 - 8
padding_sequence_len = payload_size - seq_len - timestamp_len
padding_sequence = ('A'*padding_sequence_len).encode()

for port in ports:
  sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
  sock.bind(('::', port))
  socks.append(sock)
  seq_nums.append(0)

recv_port = args.port+2

# Use dedicated socket to receive acknowledgements. This one is non-blocking. 
recv_socket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
recv_socket.bind(('::', recv_port))

# Just get an estimate of the RTT
data, addr = recv_socket.recvfrom(1500)
initial_addr = addr
for i in range(2):
  socks[i].connect(initial_addr)
if args.debug:
  print('Got connection from', initial_addr, type(initial_addr[0]))
t1 = time.time()
ret_msg = struct.pack(pack_seq_num_and_timestamp, 0, time.time())
socks[0].send(ret_msg)
data, addr = recv_socket.recvfrom(1500)
initial_rtt = time.time() - t1

# Detection part starting
# Initial rates in packets per second
recv_socket.setblocking(False)
rates = [15, 30]
latest_rtts = [initial_rtt] * len(ports)
recv_packet_len = seq_len + from_socket_len + timestamp_len
# Next socket to send from
next_socket = 0
port_indices = range(len(ports))
data_buffer = bytearray(recv_packet_len)
send_buffer = bytearray(payload_size)
send_buffer[seq_len+timestamp_len:] = padding_sequence
# We run as many cycles as necessary to detect fair queuing
for cycle_num in range(sys.maxsize):
  # Current seq nums at the beginning of the cycle
  seq_nums_beginning = list(seq_nums)
  # Seq nums when enough packet were sent 
  seq_nums_end = None
  # How many packets were acked in the current cycle
  num_acked = [0] * len(ports) 
  # Time the first ack was received
  first_ack_times = [None] * len(ports)
  # Time the second ack was received
  last_ack_times = [None] * len(ports)
  start_time = time.time()
  # Time at which enough packets were sent for the measurement
  send_end_time = None
  # Make sure to send at least one packet in each cycle
  min_time = 1/rates[0]
  # Time of the measurement. Maximum of the current rtts of both subflows. At least 100ms. 
  time_to_run = max(max(max(latest_rtts), 0.1), min_time)
  # How many packets should be sent for this measurement
  should_send = [item*time_to_run for item in rates]
  rates_in_mbit = [round(item*8*args.mtu/1000000, 1) for item in rates]
  if args.debug:
    print(f'Start {cycle_num=},{rates=},{rates_in_mbit=},{time_to_run=}')
  while True:
    current_time = time.time()
    # Check if enough packets were sent already
    if seq_nums_end is None and current_time > start_time + time_to_run:
      seq_nums_end = list(seq_nums)
      send_end_time = current_time
    try:
      while True:
        # Try to receive an acknowledgement from the client
        recv_socket.recv_into(data_buffer)
        ack_num, send_timestamp, sock_index = struct.unpack(unpack_ack_and_timestamp_and_sock_index, data_buffer)
        latest_rtts[sock_index] = current_time - send_timestamp
        assert(sock_index >=0 and sock_index <= 1)
        if ack_num >= seq_nums_beginning[sock_index] and (seq_nums_end is None or ack_num < seq_nums_end[sock_index]):
          if num_acked[sock_index] == 0:
            # First ack received for this subflow
            first_ack_times[sock_index] = current_time
          # Add ack if it is relevant for the current measurement
          num_acked[sock_index] += 1
        elif last_ack_times[sock_index] is None and seq_nums_end is not None and ack_num >= seq_nums_end[sock_index]-1:
          # This was the last ack relevant for the current measurement
          last_ack_times[sock_index] = current_time
    except OSError as e:
      # No ack to read. The socket is non-blocking. 
      pass
    if all([item is not None for item in last_ack_times]):
      break

    # The following logic determines if the next packet should be sent from
    # the first or second port and when
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
      # If we have some time until the next packet should be sent, sleep
      # Otherwise (next_send_time_delta<=0), send immediately
      time.sleep(next_send_time_delta)
    send_msg = struct.pack(pack_seq_num_and_timestamp, seq_nums[next_socket], current_time + max(next_send_time_delta, 0))
    send_buffer[:seq_len+timestamp_len] = send_msg
    # socks[next_socket].sendto(send_buffer, addr)
    socks[next_socket].send(send_buffer)
    seq_nums[next_socket] += 1
  packets_actually_sent = [seq_nums_end_i-seq_nums_beginning_i for seq_nums_beginning_i, seq_nums_end_i in zip(seq_nums_beginning, seq_nums_end)]
  # Could the link be saturated?
  sent_enough = [math.ceil(packets_actually_sent_i) + 1 >= should_send_i * 15/16 for should_send_i, packets_actually_sent_i in zip(should_send, packets_actually_sent)]
  rtts_ms = [round(item*1000) for item in latest_rtts]
  receiving_rate1 = (num_acked[0]/(last_ack_times[0]-first_ack_times[0]))
  receiving_rate2 = (num_acked[1]/(last_ack_times[1]-first_ack_times[1]))
  sending_rate1 = (packets_actually_sent[0]/(send_end_time-start_time))
  sending_rate2 = (packets_actually_sent[1]/(send_end_time-start_time))
  # Ratio of receiving rate over sending rate for the first flow
  first_ratio = receiving_rate1/sending_rate1
  # Ratio of receiving rate over sending rate for the second flow
  second_ratio = receiving_rate2/sending_rate2
  if args.debug:
    print(f'End {cycle_num=},{packets_actually_sent=},{rtts_ms=},{sent_enough=},{seq_nums_beginning=},{should_send=},{seq_nums_end=},{num_acked=},{seq_nums=},{first_ratio=},{second_ratio=}')
  
  # This means that the client only receives data at half the rate, at which the server is sending
  # This means there's severe congestion. We want this to test whether there's fair queuing!
  if second_ratio < 0.5:
    loss_ratio = first_ratio/second_ratio
    # print('send_time_diff', send_end_time-start_time, 'ack_time_diff', [last-first for first, last in zip(first_ack_times, last_ack_times)], 
    #       'first_ack_diff', first_ack_times[0]-first_ack_times[1], 'last_ack_diff', last_ack_times[0]-last_ack_times[1])
    # print('recv_rate0', num_acked[0]/(last_ack_times[0]-first_ack_times[0]), 'send_rate0', (packets_actually_sent[0]/(send_end_time-start_time)),
    #       'recv_rate1', num_acked[1]/(last_ack_times[1]-first_ack_times[1]), 'send_rate1', (packets_actually_sent[1]/(send_end_time-start_time)))
    if loss_ratio >= 1.5:
      # This means that second flow sent a lot more but couldn't get more data to the client
      confidence = min((loss_ratio-1.5)*2, 1)
      print(f'Fair queuing detected with a confidence of {round(confidence*100)}%')#, {loss_ratio=}')
    else:
      # The second flow sent more and got more data to the client
      confidence = min(1-((loss_ratio-1)*2), 1)
      print(f'First-come first-served detected with a confidence of {round(confidence*100)}%')#, {loss_ratio=}')
    break
  elif not all(sent_enough):
    managed_to_send_mbit = round((sending_rate1+sending_rate2)*8*args.mtu/1000000, 1)
    print(f'Failed to utilize the link. Tried to send {sum(rates_in_mbit)} Mbit/s but only managed {managed_to_send_mbit} Mbit/s. Aborting')
    break
  # If nothing happened, double the sending rate, to try to saturate the link
  rates = [rate*2 for rate in rates]

print('Terminating server')
