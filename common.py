import struct
# ipv4_header_len = 20
# udp_header_len =  8
seq_len = 4
ack_len = 4

minimum_payload_size = 1200

udp_ports = [13579, 13580]

padding_sequence_len = 1200-seq_len-ack_len
padding_sequence = ('A'*padding_sequence_len).encode()

packed_zero = struct.pack('!I', 0)