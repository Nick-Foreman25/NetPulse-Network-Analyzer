# database.py
import sqlite3
import os

DB_FILE = os.path.join(os.path.dirname(__file__), "..", "netpulse.db")

def get_conn():
    db_dir = os.path.dirname(DB_FILE)
    os.makedirs(db_dir, exist_ok=True)
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
    CREATE TABLE IF NOT EXISTS host_groups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        group_name TEXT UNIQUE
    )''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS hosts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        host TEXT,
        group_id INTEGER,
        FOREIGN KEY(group_id) REFERENCES host_groups(id)
    )''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS alert_thresholds (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        group_id INTEGER UNIQUE,
        max_latency REAL,
        max_packet_loss REAL,
        max_jitter REAL,
        FOREIGN KEY(group_id) REFERENCES host_groups(id)
    )''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        host TEXT,
        group_id INTEGER,
        timestamp TEXT,
        avg_latency REAL,
        packet_loss REAL,
        jitter REAL,
        min_latency REAL,
        max_latency REAL,
        dns_time REAL,
        traceroute TEXT,
        tcp_retrans_rate REAL,
        alerts TEXT,
        FOREIGN KEY(group_id) REFERENCES host_groups(id)
    )''')
    conn.commit()
    conn.close()

# Group management
def add_group(name):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO host_groups (group_name) VALUES (?)", (name,))
    conn.commit()
    conn.close()

def list_groups():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id, group_name FROM host_groups ORDER BY group_name")
    rows = c.fetchall()
    conn.close()
    return rows

def delete_group(group_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM host_groups WHERE id=?", (group_id,))
    c.execute("UPDATE hosts SET group_id=NULL WHERE group_id=?", (group_id,))
    c.execute("DELETE FROM alert_thresholds WHERE group_id=?", (group_id,))
    conn.commit()
    conn.close()

# Hosts
def add_host(host, group_id=None):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO hosts (host, group_id) VALUES (?, ?)", (host, group_id))
    conn.commit()
    conn.close()

def list_hosts():
    conn = get_conn()
    c = conn.cursor()
    c.execute('''SELECT hosts.id, hosts.host, hosts.group_id, host_groups.group_name
                 FROM hosts LEFT JOIN host_groups ON hosts.group_id = host_groups.id
                 ORDER BY host_groups.group_name NULLS LAST, hosts.host''')
    rows = c.fetchall()
    conn.close()
    return rows

def delete_host(host_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM hosts WHERE id=?", (host_id,))
    conn.commit()
    conn.close()

# Thresholds
def set_thresholds(group_id, max_latency, max_packet_loss, max_jitter):
    conn = get_conn()
    c = conn.cursor()
    c.execute('''INSERT INTO alert_thresholds (group_id, max_latency, max_packet_loss, max_jitter)
                 VALUES (?, ?, ?, ?)
                 ON CONFLICT(group_id) DO UPDATE SET max_latency=excluded.max_latency,
                 max_packet_loss=excluded.max_packet_loss, max_jitter=excluded.max_jitter''',
              (group_id, max_latency, max_packet_loss, max_jitter))
    conn.commit()
    conn.close()

def get_thresholds(group_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT max_latency, max_packet_loss, max_jitter FROM alert_thresholds WHERE group_id=?", (group_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {"max_latency": row[0], "max_packet_loss": row[1], "max_jitter": row[2]}
    else:
        # default sensible thresholds if none defined
        return {"max_latency": 200.0, "max_packet_loss": 5.0, "max_jitter": 50.0}

# Results saving & querying
def save_result(host, group_id, timestamp, avg_latency, packet_loss, jitter, min_latency, max_latency, dns_time, traceroute_text, tcp_retrans_rate, alerts_text):
    conn = get_conn()
    c = conn.cursor()
    c.execute('''INSERT INTO results (host, group_id, timestamp, avg_latency, packet_loss, jitter, min_latency, max_latency, dns_time, traceroute, tcp_retrans_rate, alerts)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (host, group_id, timestamp, avg_latency, packet_loss, jitter, min_latency, max_latency, dns_time, traceroute_text, tcp_retrans_rate, alerts_text))
    conn.commit()
    conn.close()

def query_results(start_ts=None, end_ts=None, group_ids=None):
    conn = get_conn()
    c = conn.cursor()
    q = "SELECT * FROM results WHERE 1=1"
    params = []
    if start_ts:
        q += " AND timestamp >= ?"
        params.append(start_ts)
    if end_ts:
        q += " AND timestamp <= ?"
        params.append(end_ts)
    if group_ids:
        q += " AND group_id IN ({})".format(",".join("?"*len(group_ids)))
        params.extend(group_ids)
    q += " ORDER BY timestamp ASC"
    c.execute(q, params)
    rows = c.fetchall()
    conn.close()
    return rows
