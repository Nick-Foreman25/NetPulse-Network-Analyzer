# main_app.py - main application code (derived from prior large UI)
# ui.py
import sys
import threading
import time
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit,
                             QLabel, QTextEdit, QTableWidget, QTableWidgetItem, QComboBox, QSpinBox,
                             QFileDialog, QMessageBox, QTabWidget, QGroupBox, QDateEdit, QCheckBox)
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QDate
import database
import utils
import network_tests
import reporting
from datetime import datetime
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # for report generation
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from scheduler import schedule_job, start_scheduler, stop_scheduler

# Worker thread to run tests for hosts
class TestWorker(QThread):
    update = pyqtSignal(dict)  # emits dict with host and stats

    def __init__(self, hosts_with_groups, interval=10, once=False):
        super().__init__()
        self.hosts_with_groups = hosts_with_groups  # list of tuples: (host, group_id)
        self.interval = interval
        self._running = True
        self.once = once

    def run(self):
        while self._running:
            for host, group_id in self.hosts_with_groups:
                if not self._running:
                    break
                stats = network_tests.ping_stats(host, count=5)
                dns_time = network_tests.dns_lookup(host)
                tracer = network_tests.traceroute(host)
                timestamp = utils.now_iso()
                # Check alerts
                thresholds = database.get_thresholds(group_id) if group_id else {"max_latency":200,"max_packet_loss":5,"max_jitter":50}
                alerts = []
                try:
                    if stats['avg_latency'] is not None and stats['avg_latency'] > thresholds['max_latency']:
                        alerts.append(f"Latency {stats['avg_latency']:.1f}ms > {thresholds['max_latency']}ms")
                    if stats['packet_loss'] is not None and stats['packet_loss'] > thresholds['max_packet_loss']:
                        alerts.append(f"PacketLoss {stats['packet_loss']:.1f}% > {thresholds['max_packet_loss']}%")
                    if stats['jitter'] is not None and stats['jitter'] > thresholds['max_jitter']:
                        alerts.append(f"Jitter {stats['jitter']:.1f}ms > {thresholds['max_jitter']}ms")
                except Exception:
                    pass
                alerts_text = "; ".join(alerts) if alerts else ""
                database.save_result(host, group_id, timestamp,
                                     stats['avg_latency'] if stats['avg_latency'] else None,
                                     stats['packet_loss'] if stats['packet_loss'] else None,
                                     stats['jitter'] if stats['jitter'] else None,
                                     stats['min_latency'] if stats.get('min_latency') else None,
                                     stats['max_latency'] if stats.get('max_latency') else None,
                                     dns_time if dns_time else None,
                                     tracer,
                                     alerts_text)
                self.update.emit({
                    "host": host,
                    "group_id": group_id,
                    "timestamp": timestamp,
                    "stats": stats,
                    "dns_time": dns_time,
                    "traceroute": tracer,
                    "alerts": alerts_text
                })
            if self.once:
                break
            # sleep
            for _ in range(int(self.interval)):
                if not self._running:
                    break
                time.sleep(1)

    def stop(self):
        self._running = False

# Matplotlib canvas for live graphs
class LivePlot(FigureCanvas):
    def __init__(self, parent=None, width=5, height=3, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super().__init__(fig)
        self.setParent(parent)
        self._data = {}  # host -> list of (timestamp, value)

    def add_point(self, host, timestamp, value):
        if value is None:
            return
        self._data.setdefault(host, []).append((timestamp, value))
        # keep last N points
        if len(self._data[host]) > 2000:
            self._data[host] = self._data[host][-2000:]
        self.draw_plot()

    def draw_plot(self):
        self.axes.clear()
        for host, points in self._data.items():
            xs = [pd.to_datetime(p[0]) for p in points]
            ys = [p[1] for p in points]
            self.axes.plot(xs, ys, marker='o', label=host)
        self.axes.legend(loc='upper left', fontsize='small', ncol=1)
        self.axes.set_ylabel('ms')
        self.axes.set_xlabel('Time')
        self.axes.grid(True)
        self.draw()

    def clear(self):
        self._data = {}
        self.axes.clear()
        self.draw()

# Main GUI
class NetPulseApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NetPulse")
        self.resize(1000, 700)
        # init db
        database.init_db()
        self.worker = None
        self.scheduled_jobs = {}  # job_id -> job info

        layout = QVBoxLayout()
        tabs = QTabWidget()
        tabs.addTab(self.setup_hosts_tab(), "Hosts & Groups")
        tabs.addTab(self.setup_schedule_tab(), "Scheduled Tests")
        tabs.addTab(self.setup_manual_tab(), "Manual Test")
        tabs.addTab(self.setup_history_tab(), "Historical Reports")
        layout.addWidget(tabs)
        self.setLayout(layout)

    # Tab 1: Hosts & Groups
    def setup_hosts_tab(self):
    	widget = QWidget()
    	v = QVBoxLayout()

    # -------------------- Group Controls --------------------
    	grp_box = QGroupBox("Groups")
    	gbox_layout = QHBoxLayout()

    	self.group_name_input = QLineEdit()
    	add_group_btn = QPushButton("Add Group")
    	add_group_btn.clicked.connect(self.add_group)

    	self.group_select = QComboBox()

    	gbox_layout.addWidget(QLabel("Group Name:"))
    	gbox_layout.addWidget(self.group_name_input)
    	gbox_layout.addWidget(add_group_btn)
    	gbox_layout.addWidget(QLabel("Assign to Group:"))
    	gbox_layout.addWidget(self.group_select)

    	grp_box.setLayout(gbox_layout)
    	v.addWidget(grp_box)

    # -------------------- Host Add Controls --------------------
    	host_box = QGroupBox("Add Hosts / Ranges")
    	hbox = QHBoxLayout()

    	self.single_host_input = QLineEdit()
    	add_host_btn = QPushButton("Add Host")
    	add_host_btn.clicked.connect(self.add_single_host)

    	self.range_input = QLineEdit()
    	add_range_btn = QPushButton("Add Range")
    	add_range_btn.clicked.connect(self.add_range)

    	hbox.addWidget(QLabel("Single Host / FQDN:"))
    	hbox.addWidget(self.single_host_input)
    	hbox.addWidget(add_host_btn)
    	hbox.addWidget(QLabel("IP Range (start-end):"))
    	hbox.addWidget(self.range_input)
    	hbox.addWidget(add_range_btn)

    	host_box.setLayout(hbox)
    	v.addWidget(host_box)

    # -------------------- Hosts Table --------------------
    	self.host_table = QTableWidget()
    	self.host_table.setColumnCount(4)
    	self.host_table.setHorizontalHeaderLabels(["ID", "Host", "Group", "Remove"])
    	v.addWidget(self.host_table)

    	refresh_btn = QPushButton("Refresh Host List")
    	refresh_btn.clicked.connect(self.refresh_hosts)
    	v.addWidget(refresh_btn)

    # -------------------- Threshold Controls --------------------
    	thr_box = QGroupBox("Group Alert Thresholds (ms / %)")
    	thr_layout = QHBoxLayout()

    # Create thr_group_select BEFORE calling refresh_groups
    	self.thr_group_select = QComboBox()
    	self.thr_max_latency = QSpinBox(); self.thr_max_latency.setRange(1,100000); 	self.thr_max_latency.setValue(200)
    	self.thr_pkt_loss = QSpinBox(); self.thr_pkt_loss.setRange(0,100); 	self.thr_pkt_loss.setValue(5)
    	self.thr_jitter = QSpinBox(); self.thr_jitter.setRange(0,100000); self.thr_jitter.setValue(50)
    	set_thr_btn = QPushButton("Set Thresholds")
    	set_thr_btn.clicked.connect(self.set_thresholds)

    	thr_layout.addWidget(QLabel("Group:")); thr_layout.addWidget(self.thr_group_select)
    	thr_layout.addWidget(QLabel("Max Latency (ms):")); thr_layout.addWidget(self.thr_max_latency)
    	thr_layout.addWidget(QLabel("Max Packet Loss (%):")); thr_layout.addWidget(self.thr_pkt_loss)
    	thr_layout.addWidget(QLabel("Max Jitter (ms):")); thr_layout.addWidget(self.thr_jitter)
    	thr_layout.addWidget(set_thr_btn)

    	thr_box.setLayout(thr_layout)
    	v.addWidget(thr_box)

    # -------------------- Final Setup --------------------
    	widget.setLayout(v)

    # Now that both group_select and thr_group_select exist, safe to call refresh_groups
    	self.refresh_groups()
    	self.refresh_hosts()

    	return widget

    def add_group(self):
        name = self.group_name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation", "Group name required")
            return
        database.add_group(name)
        self.group_name_input.clear()
        self.refresh_groups()

    def refresh_groups(self):
        groups = database.list_groups()
        self.group_select.clear()
        self.thr_group_select.clear()
        self.group_select.addItem("None", None)
        for gid, name in groups:
            self.group_select.addItem(name, gid)
            self.thr_group_select.addItem(name, gid)

    def add_single_host(self):
        host = self.single_host_input.text().strip()
        if not host:
            QMessageBox.warning(self, "Validation", "Host/IP required")
            return
        group_id = self.group_select.currentData()
        database.add_host(host, group_id)
        self.single_host_input.clear()
        self.refresh_hosts()

    def add_range(self):
        rng = self.range_input.text().strip()
        if not rng:
            QMessageBox.warning(self, "Validation", "Range required")
            return
        group_id = self.group_select.currentData()
        ips = utils.expand_ip_range(rng)
        for ip in ips:
            database.add_host(ip, group_id)
        self.range_input.clear()
        self.refresh_hosts()

    def refresh_hosts(self):
        rows = database.list_hosts()
        self.host_table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            host_id, host, group_id, group_name = row
            self.host_table.setItem(i, 0, QTableWidgetItem(str(host_id)))
            self.host_table.setItem(i, 1, QTableWidgetItem(host))
            self.host_table.setItem(i, 2, QTableWidgetItem(group_name if group_name else "None"))
            rem_btn = QPushButton("Remove")
            def make_remove(rid):
                return lambda: self.remove_host(rid)
            rem_btn.clicked.connect(make_remove(host_id))
            self.host_table.setCellWidget(i, 3, rem_btn)

    def remove_host(self, host_id):
        database.delete_host(host_id)
        self.refresh_hosts()

    def set_thresholds(self):
        gid = self.thr_group_select.currentData()
        if gid is None:
            QMessageBox.warning(self, "Validation", "Select a group")
            return
        database.set_thresholds(gid, float(self.thr_max_latency.value()), float(self.thr_pkt_loss.value()), float(self.thr_jitter.value()))
        QMessageBox.information(self, "Success", "Thresholds updated")

    # Tab 2: Scheduling
    def setup_schedule_tab(self):
        widget = QWidget()
        v = QVBoxLayout()

        # Select groups/hosts
        box = QGroupBox("Schedule Configuration")
        blayout = QHBoxLayout()
        self.schedule_group_select = QComboBox()
        self.refresh_groups()
        blayout.addWidget(QLabel("Run group:"))
        blayout.addWidget(self.schedule_group_select)
        blayout.addWidget(QLabel("Interval seconds:"))
        self.schedule_interval = QSpinBox(); self.schedule_interval.setRange(10, 86400); self.schedule_interval.setValue(60)
        blayout.addWidget(self.schedule_interval)
        self.schedule_job_name = QLineEdit("job1")
        blayout.addWidget(QLabel("Job name:")); blayout.addWidget(self.schedule_job_name)
        add_job_btn = QPushButton("Start Schedule")
        add_job_btn.clicked.connect(self.start_schedule)
        stop_job_btn = QPushButton("Stop Schedule")
        stop_job_btn.clicked.connect(self.stop_schedule)
        blayout.addWidget(add_job_btn); blayout.addWidget(stop_job_btn)
        box.setLayout(blayout)
        v.addWidget(box)

        # Export options
        export_box = QGroupBox("Export Options After Run")
        ex_layout = QHBoxLayout()
        self.export_format = QComboBox(); self.export_format.addItems(["Excel","PDF"])
        self.export_folder_input = QLineEdit()
        sel_folder_btn = QPushButton("Select Folder")
        sel_folder_btn.clicked.connect(self.select_export_folder)
        ex_layout.addWidget(QLabel("Format:")); ex_layout.addWidget(self.export_format)
        ex_layout.addWidget(QLabel("Folder:")); ex_layout.addWidget(self.export_folder_input); ex_layout.addWidget(sel_folder_btn)
        export_box.setLayout(ex_layout)
        v.addWidget(export_box)

        # Status log
        self.schedule_log = QTextEdit()
        self.schedule_log.setReadOnly(True)
        v.addWidget(self.schedule_log)

        widget.setLayout(v)
        return widget

    def select_export_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Export Folder")
        if folder:
            self.export_folder_input.setText(folder)

    def start_schedule(self):
        group_id = self.schedule_group_select.currentData()
        if group_id is None:
            QMessageBox.warning(self, "Validation", "Select a group to schedule")
            return
        job_name = self.schedule_job_name.text().strip()
        if not job_name:
            QMessageBox.warning(self, "Validation", "Job name required")
            return
        interval = int(self.schedule_interval.value())
        # prepare hosts for group
        hosts_rows = [r for r in database.list_hosts() if r[2] == group_id]  # filter by group_id
        hosts = [(r[1], r[2]) for r in hosts_rows]
        if not hosts:
            QMessageBox.warning(self, "Validation", "No hosts in selected group")
            return
        # define job function
        def job_run(hosts_list, export_folder, export_format):
            self.schedule_log.append(f"{datetime.utcnow().isoformat()} - Running scheduled test for group_id={group_id}")
            # run once via TestWorker-like loop
            for host, gid in hosts_list:
                stats = network_tests.ping_stats(host, count=5)
                dns_time = network_tests.dns_lookup(host)
                tracer = network_tests.traceroute(host)
                timestamp = utils.now_iso()
                thresholds = database.get_thresholds(gid) if gid else {"max_latency":200,"max_packet_loss":5,"max_jitter":50}
                alerts = []
                try:
                    if stats['avg_latency'] is not None and stats['avg_latency'] > thresholds['max_latency']:
                        alerts.append(f"Latency {stats['avg_latency']:.1f}ms > {thresholds['max_latency']}ms")
                    if stats['packet_loss'] is not None and stats['packet_loss'] > thresholds['max_packet_loss']:
                        alerts.append(f"PacketLoss {stats['packet_loss']:.1f}% > {thresholds['max_packet_loss']}%")
                    if stats['jitter'] is not None and stats['jitter'] > thresholds['max_jitter']:
                        alerts.append(f"Jitter {stats['jitter']:.1f}ms > {thresholds['max_jitter']}ms")
                except Exception:
                    pass
                alerts_text = "; ".join(alerts) if alerts else ""
                database.save_result(host, gid, timestamp,
                                     stats['avg_latency'] if stats['avg_latency'] else None,
                                     stats['packet_loss'] if stats['packet_loss'] else None,
                                     stats['jitter'] if stats['jitter'] else None,
                                     stats['min_latency'] if stats.get('min_latency') else None,
                                     stats['max_latency'] if stats.get('max_latency') else None,
                                     dns_time if dns_time else None,
                                     tracer,
                                     alerts_text)
            # export after run
            try:
                rows = database.query_results()
                folder = export_folder
                if export_format == "Excel":
                    path = f"{folder}/NetPulse_Schedule_{job_name}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.xlsx"
                    reporting.export_to_excel(path, rows)
                    self.schedule_log.append(f"Exported Excel to {path}")
                else:
                    path = f"{folder}/NetPulse_Schedule_{job_name}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.pdf"
                    reporting.export_to_pdf(path, rows)
                    self.schedule_log.append(f"Exported PDF to {path}")
            except Exception as e:
                self.schedule_log.append(f"Export error: {e}")

        # schedule job
        start_scheduler()
        try:
            schedule_job(job_name, job_run, {'type':'interval', 'seconds':interval}, (hosts, self.export_folder_input.text(), self.export_format.currentText()))
            self.schedule_log.append(f"Scheduled job '{job_name}' every {interval}s for group id {group_id}")
        except Exception as e:
            QMessageBox.critical(self, "Scheduler Error", str(e))

    def stop_schedule(self):
        job_name = self.schedule_job_name.text().strip()
        if not job_name:
            QMessageBox.warning(self, "Validation", "Job name required to stop")
            return
        try:
            from apscheduler.schedulers.base import JobLookupError
            start_scheduler()
            # remove job
            from scheduler import _scheduler
            if _scheduler:
                _scheduler.remove_job(job_name)
                self.schedule_log.append(f"Stopped job {job_name}")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not stop job: {e}")

    # Tab 3: Manual Test
    def setup_manual_tab(self):
        widget = QWidget()
        v = QVBoxLayout()

        ctrl_layout = QHBoxLayout()
        self.manual_group_select = QComboBox()
        self.refresh_groups()
        ctrl_layout.addWidget(QLabel("Group:")); ctrl_layout.addWidget(self.manual_group_select)
        self.manual_hosts_combo = QComboBox()
        ctrl_layout.addWidget(QLabel("Host (or All in group):")); ctrl_layout.addWidget(self.manual_hosts_combo)
        load_hosts_btn = QPushButton("Load Hosts for Group")
        load_hosts_btn.clicked.connect(self.load_hosts_for_group)
        ctrl_layout.addWidget(load_hosts_btn)
        run_btn = QPushButton("Run Test Now")
        run_btn.clicked.connect(self.run_manual_test)
        ctrl_layout.addWidget(run_btn)
        v.addLayout(ctrl_layout)

        # Real-time plot
        self.live_plot = LivePlot(self, width=8, height=3, dpi=100)
        v.addWidget(self.live_plot)

        # Results table/log
        self.manual_log = QTextEdit()
        self.manual_log.setReadOnly(True)
        v.addWidget(self.manual_log)

        # Export
        export_layout = QHBoxLayout()
        self.manual_export_format = QComboBox(); self.manual_export_format.addItems(["Excel","PDF"])
        export_btn = QPushButton("Export Recent Results")
        export_btn.clicked.connect(self.export_manual_results)
        export_layout.addWidget(QLabel("Export Format:")); export_layout.addWidget(self.manual_export_format); export_layout.addWidget(export_btn)
        v.addLayout(export_layout)

        widget.setLayout(v)
        return widget

    def load_hosts_for_group(self):
        gid = self.manual_group_select.currentData()
        hosts = [r for r in database.list_hosts() if r[2] == gid] if gid else database.list_hosts()
        self.manual_hosts_combo.clear()
        self.manual_hosts_combo.addItem("All", None)
        for r in hosts:
            self.manual_hosts_combo.addItem(r[1], r[1])

    def run_manual_test(self):
        gid = self.manual_group_select.currentData()
        selected_host = self.manual_hosts_combo.currentData()
        hosts = []
        if selected_host:
            # single host
            hosts = [(selected_host, gid)]
        else:
            # all hosts in group
            hosts = [(r[1], r[2]) for r in database.list_hosts() if r[2] == gid]
        if not hosts:
            QMessageBox.warning(self, "Validation", "No hosts selected")
            return
        # run in background worker (single run)
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, "Worker running", "Another test is running")
            return
        self.live_plot.clear()
        self.worker = TestWorker(hosts, interval=5, once=True)
        self.worker.update.connect(self.handle_worker_update)
        self.worker.start()

    def handle_worker_update(self, data):
        host = data['host']
        stats = data['stats']
        ts = data['timestamp']
        self.manual_log.append(f"{ts} - {host} - avg: {stats.get('avg_latency')}ms loss: {stats.get('packet_loss')}% jitter: {stats.get('jitter')} alerts: {data.get('alerts')}")
        if stats.get('avg_latency') is not None:
            self.live_plot.add_point(host, ts, stats.get('avg_latency'))

    def export_manual_results(self):
        # export all results for group within last day by default
        gid = self.manual_group_select.currentData()
        rows = database.query_results()
        folder = QFileDialog.getExistingDirectory(self, "Select Export Folder")
        if not folder:
            return
        fmt = self.manual_export_format.currentText()
        if fmt == "Excel":
            path = f"{folder}/NetPulse_Manual_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.xlsx"
            reporting.export_to_excel(path, rows)
            QMessageBox.information(self, "Exported", f"Excel saved to {path}")
        else:
            path = f"{folder}/NetPulse_Manual_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.pdf"
            reporting.export_to_pdf(path, rows)
            QMessageBox.information(self, "Exported", f"PDF saved to {path}")

    # Tab 4: History
    def setup_history_tab(self):
        widget = QWidget()
        v = QVBoxLayout()
        h = QHBoxLayout()
        self.history_group_select = QComboBox()
        self.refresh_groups()
        h.addWidget(QLabel("Group:")); h.addWidget(self.history_group_select)
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate().addDays(-7))
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate())
        h.addWidget(QLabel("Start:")); h.addWidget(self.start_date)
        h.addWidget(QLabel("End:")); h.addWidget(self.end_date)
        load_btn = QPushButton("Load")
        load_btn.clicked.connect(self.load_history)
        h.addWidget(load_btn)
        v.addLayout(h)
        # Table and plot
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(6)
        self.history_table.setHorizontalHeaderLabels(["Timestamp","Host","Avg Latency","PacketLoss","Jitter","Alerts"])
        v.addWidget(self.history_table)
        self.history_plot = LivePlot(self, width=8, height=3)
        v.addWidget(self.history_plot)
        # Export
        export_btn = QPushButton("Export Filtered Results")
        export_btn.clicked.connect(self.export_history)
        v.addWidget(export_btn)
        widget.setLayout(v)
        return widget

    def load_history(self):
        gid = self.history_group_select.currentData()
        start_ts = self.start_date.date().toString("yyyy-MM-dd") + " 00:00:00"
        end_ts = self.end_date.date().toString("yyyy-MM-dd") + " 23:59:59"
        group_ids = [gid] if gid else None
        rows = database.query_results(start_ts=start_ts, end_ts=end_ts, group_ids=group_ids)
        self.history_table.setRowCount(len(rows))
        self.history_plot.clear()
        for i,row in enumerate(rows):
            _, host, _, timestamp, avg, pkt, jitter, *_ , alerts = row
            self.history_table.setItem(i,0,QTableWidgetItem(timestamp))
            self.history_table.setItem(i,1,QTableWidgetItem(host))
            self.history_table.setItem(i,2,QTableWidgetItem(str(avg)))
            self.history_table.setItem(i,3,QTableWidgetItem(str(pkt)))
            self.history_table.setItem(i,4,QTableWidgetItem(str(jitter)))
            self.history_table.setItem(i,5,QTableWidgetItem(str(alerts)))
            if avg is not None:
                self.history_plot.add_point(host, timestamp, avg)

    def export_history(self):
        gid = self.history_group_select.currentData()
        start_ts = self.start_date.date().toString("yyyy-MM-dd") + " 00:00:00"
        end_ts = self.end_date.date().toString("yyyy-MM-dd") + " 23:59:59"
        group_ids = [gid] if gid else None
        rows = database.query_results(start_ts=start_ts, end_ts=end_ts, group_ids=group_ids)
        folder = QFileDialog.getExistingDirectory(self, "Select Export Folder")
        if not folder:
            return
        fmt, _ = QFileDialog.getSaveFileName(self, "Save Report", folder + "/NetPulse_Report", "Excel Files (*.xlsx);;PDF Files (*.pdf)")
        if not fmt:
            return
        if fmt.endswith(".xlsx"):
            reporting.export_to_excel(fmt, rows)
            QMessageBox.information(self, "Exported", f"Excel saved to {fmt}")
        else:
            reporting.export_to_pdf(fmt, rows)
            QMessageBox.information(self, "Exported", f"PDF saved to {fmt}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = NetPulseApp()
    window.show()
    sys.exit(app.exec_())
