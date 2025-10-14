# network_tests.py
from pythonping import ping
import dns.resolver
import subprocess
import statistics
import time
from tcp_monitor import monitor_retransmissions

def ping_stats(host, count=5, timeout=2):
    """Returns dict with avg_latency (ms), packet_loss (%), jitter (ms), min_latency, max_latency"""
    try:
        responses = ping(host, count=count, timeout=timeout, size=56)
        latencies = [resp.time_elapsed_ms for resp in responses]
        successes = [resp.success for resp in responses]
        if len(latencies) == 0:
            return {"avg_latency": None, "packet_loss": 100.0, "jitter": None, "min_latency": None, "max_latency": None}
        packet_loss = 100.0 * (1 - (sum(successes) / len(successes)))
        jitter = statistics.stdev(latencies) if len(latencies) > 1 else 0.0
        avg_latency = sum(latencies)/len(latencies)
        return {"avg_latency": avg_latency, "packet_loss": packet_loss, "jitter": jitter, "min_latency": min(latencies), "max_latency": max(latencies)}
    except Exception as e:
        return {"avg_latency": None, "packet_loss": 100.0, "jitter": None, "min_latency": None, "max_latency": None}

def dns_lookup(host):
    try:
        resolver = dns.resolver.Resolver()
        start = time.time()
        resolver.resolve(host)
        elapsed_ms = (time.time() - start) * 1000.0
        return elapsed_ms
    except Exception:
        return None

def traceroute(host, max_hops=30):
    """Uses platform traceroute (tracert on Windows). Returns text output."""
    try:
        import platform
        if platform.system().lower().startswith("win"):
            cmd = ["tracert", "-d", host]
        else:
            cmd = ["traceroute", "-n", host]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return p.stdout
    except Exception as e:
        return str(e)

def measure_tcp_retrans(duration=5, iface=None):
    try:
        res = monitor_retransmissions(duration=duration, iface=iface)
        return res  # includes rate
    except Exception as e:
        return {'total':0,'retransmissions':0,'rate':0.0,'duration':0}
