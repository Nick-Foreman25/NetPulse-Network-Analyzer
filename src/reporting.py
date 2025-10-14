# reporting.py
import pandas as pd
import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import matplotlib.pyplot as plt
from datetime import datetime

def df_from_query(rows):
    cols = ['id','host','group_id','timestamp','avg_latency','packet_loss','jitter','min_latency','max_latency','dns_time','traceroute','tcp_retrans_rate','alerts']
    return pd.DataFrame(rows, columns=cols)

def export_to_excel(save_path, rows):
    df = df_from_query(rows)
    df.to_excel(save_path, index=False)

def export_to_pdf(save_path, rows):
    df = df_from_query(rows)
    c = canvas.Canvas(save_path, pagesize=letter)
    width, height = letter
    y = height - 50
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, f"NetPulse Report - {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    y -= 30
    c.setFont("Helvetica", 10)
    grouped = df.groupby('host')
    for host, g in grouped:
        if y < 140:
            c.showPage()
            y = height - 50
        c.drawString(40, y, f"Host: {host} | Entries: {len(g)}")
        y -= 14
        try:
            avg_latency = g['avg_latency'].mean() if not g['avg_latency'].isnull().all() else None
            pkt_loss = g['packet_loss'].mean() if not g['packet_loss'].isnull().all() else None
            retrans = g['tcp_retrans_rate'].mean() if 'tcp_retrans_rate' in g and not g['tcp_retrans_rate'].isnull().all() else None
            c.drawString(50, y, f"Avg Latency (ms): {avg_latency:.2f}  | Avg Packet Loss (%): {pkt_loss:.2f}  | Avg TCP Retrans (%): {retrans:.2f}" if avg_latency is not None else "No data")
        except Exception:
            c.drawString(50, y, "Summary data not available")
        y -= 12
        # small plot
        try:
            fig, ax = plt.subplots(figsize=(4,1.2))
            ax.plot(pd.to_datetime(g['timestamp']), g['avg_latency'], marker='o')
            ax.set_title(host)
            ax.set_ylabel('ms')
            ax.grid(True)
            buf = io.BytesIO()
            plt.tight_layout()
            fig.savefig(buf, format='png')
            plt.close(fig)
            buf.seek(0)
            img = ImageReader(buf)
            c.drawImage(img, 50, y-60, width=400, height=60)
            y -= 70
        except Exception:
            y -= 10
    c.save()
