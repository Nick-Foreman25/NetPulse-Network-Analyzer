# tcp_monitor.py
# Uses scapy to sniff TCP packets and detect retransmissions.
from scapy.all import sniff, TCP, IP
from collections import defaultdict
import time

def monitor_retransmissions(duration=5, iface=None, filter_expr='tcp'):
    """Sniffs traffic for 'duration' seconds and returns retransmission metrics.
    Returns dict: {'total': int, 'retransmissions': int, 'rate': float} where rate is percent."""
    seq_seen = defaultdict(set)
    retransmissions = 0
    total_packets = 0
    start_time = time.time()

    def process_packet(pkt):
        nonlocal retransmissions, total_packets
        if IP in pkt and TCP in pkt:
            total_packets += 1
            try:
                flow_id = (pkt[IP].src, pkt[IP].dst, pkt[TCP].sport, pkt[TCP].dport)
                seq = int(pkt[TCP].seq)
                if seq in seq_seen[flow_id]:
                    retransmissions += 1
                else:
                    seq_seen[flow_id].add(seq)
            except Exception:
                pass

    sniff(prn=process_packet, filter=filter_expr, iface=iface, timeout=duration, store=False)
    rate = (retransmissions / total_packets * 100.0) if total_packets else 0.0
    return {'total': total_packets, 'retransmissions': retransmissions, 'rate': rate, 'duration': duration}
