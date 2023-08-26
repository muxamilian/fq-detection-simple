import struct
# ipv4_header_len = 20
# udp_header_len =  8
seq_len = 4
ack_len = 4

minimum_payload_size = 1200

udp_ports = [13579, 13580]

padding_sequence_len = 1200-seq_len-ack_len
padding_sequence = ('A'*padding_sequence_len).encode()

def generate_message(seq_num, ack_num):
    return struct.pack('!I', seq_num) + struct.pack('!I', ack_num) + padding_sequence

def decode_message(message):
    seq_num = struct.unpack('!I', message[:4])[0]
    ack_num = struct.unpack('!I', message[4:8])[0]
    return seq_num, ack_num