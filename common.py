import struct
# ipv4_header_len = 20
# udp_header_len =  8
seq_len = 4
from_socket_len = 1

minimum_payload_size = 1200

ports = [13579, 13580]

padding_sequence_len = 1200-seq_len-from_socket_len
padding_sequence = ('A'*padding_sequence_len).encode()
inf = float('inf')