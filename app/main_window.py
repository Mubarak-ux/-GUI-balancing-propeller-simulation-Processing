"""Jendela utama aplikasi."""

import collections
import math
import os
import time

import numpy as np
import pyqtgraph as pg
from PySide6 import QtCore, QtGui, QtWidgets

from .hw_stream import TelemetryStream
from .config import (ACCENT, AMBER, BORDER, GREEN, MUTED, PLOT_BG, PURPLE,
                     RED)
from .metrics import (COL_D, COL_I, COL_MEAS, COL_P, COL_SP, COL_T, COL_TH,
                      COL_U, COL_W, DASH, METRIC_KEYS, compute_metrics)
from .hw_backend import DATA_DIR, HAVE_SERIAL, HardwareBackend, list_ports
from .sim_backend import SimBackend
from .widgets.beam_view import BeamView
from .widgets.controls import Card, Metric, Param

Qt = QtCore.Qt

# ----------------------------------------------------------------------------
# IDENTITAS KELOMPOK 
# ----------------------------------------------------------------------------
GROUP_NAME = "Kelompok 1"
MEMBERS = [
    ("Mirza Pramiandra Bhirawa", "25/561291/SV/26548"),
    ("Iqbal Rasshid Mubarak", "25/567537/SV/27187"),
    ("Muhammad Ikhwan Ghozy", "25/562030/SV/26722"),
]

# ----------------------------------------------------------------------------
# SKENARIO UJI OTOMATIS
#   (nama, kondisi awal, perubahan)
#   kondisi awal : dict(sp=derajat, load=(massa_kg, posisi_m))
#   perubahan    : ("sp", derajat) atau ("load", (massa_kg, posisi_m))
# Tiap skenario: state di-reset -> fase "settle" dengan kondisi awal ->
# perubahan diterapkan -> fase "ukur" -> metrik dicatat.
# Semua fase dihitung dalam WAKTU SIMULASI, jadi aman saat di-pause.
# ----------------------------------------------------------------------------
SCENARIOS = [
    ("Step 0\u00b0 \u2192 +10\u00b0", dict(sp=0.0), ("sp", 10.0)),
    ("Step 0\u00b0 \u2192 \u221210\u00b0", dict(sp=0.0), ("sp", -10.0)),
    ("Step +10\u00b0 \u2192 0\u00b0", dict(sp=10.0), ("sp", 0.0)),
    ("Beban 200 g @ 10 cm", dict(sp=0.0), ("load", (0.2, 0.10))),
    ("Beban 400 g @ 15 cm", dict(sp=0.0), ("load", (0.4, 0.15))),
    ("Lepas beban 200 g @ 10 cm", dict(sp=0.0, load=(0.2, 0.10)), ("load", (0.0, 0.10))),
]
SCN_SETTLE_S = 4.0    # detik simulasi sebelum perubahan diterapkan
SCN_MEASURE_S = 8.0   # detik simulasi pengukuran setelah perubahan

SP_LIMIT = 20.0       # batas slider setpoint (derajat)
SP_STEP = 5.0         # besar tombol step setpoint
SETTLING_CRIT = 0.02  # kriteria settling 2 %

METRIC_TIPS = {
    "overshoot": "Overshoot maksimum (Mp) relatif terhadap besar step:\n"
                 "Mp = (\u03b8 puncak \u2212 \u03b8 akhir) / |step| \u00d7 100 %\n"
                 "Hanya untuk step setpoint.",
    "rise": "Rise time (tr): waktu respons naik dari 10 % ke 90 % besar step.\n"
            "Hanya untuk step setpoint.",
    "peak_time": "Peak time (tp): waktu dari event sampai puncak respons.\n"
                 "Step setpoint: puncak overshoot (\u2014 jika tidak ada overshoot).\n"
                 "Gangguan beban: saat deviasi terbesar.",
    "settling": "Settling time (ts): waktu sampai |e| tetap di dalam band toleransi.\n"
                "Step setpoint: band \u00b12 % dari besar step.\n"
                "Gangguan beban: band \u00b10.5\u00b0.\n"
                "e dihaluskan (moving average 0.2 s) agar noise sensor\n"
                "tidak membuat respons dianggap belum settle.\n"
                "Band ditampilkan sebagai area biru di grafik Response.",
    "error": "Steady-state error (ess): rata-rata e = setpoint \u2212 \u03b8 selama\n"
             "1 s terakhir. Muncul setelah 2 s sejak event.",
    "deviation": "Deviasi puncak: |e| maksimum setelah gangguan beban.\n"
                 "Hanya untuk gangguan beban.",
}
METRIC_TITLES = {
    "overshoot": "Overshoot (Mp)",
    "rise": "Rise time (tr)",
    "peak_time": "Peak time (tp)",
    "settling": "Settling 2% (ts)",
    "error": "Steady error (ess)",
    "deviation": "Peak deviation",
}
METRIC_COLORS = {
    "overshoot": ACCENT, "rise": ACCENT, "peak_time": ACCENT,
    "settling": PURPLE, "error": GREEN, "deviation": RED,
}


# ----------------------------------------------------------------------------
# JENDELA UTAMA
# ----------------------------------------------------------------------------
class MainWindow(QtWidgets.QMainWindow):
    TICK_MS = 20            # 50 Hz refresh UI
    WINDOW_S = 8.0          # rentang grafik (detik)
    EVENT_MAX_S = 60.0      # maksimum data yang disimpan per event
    PROP_IDLE_DPS = 900.0   # deg/s, putaran idle
    PROP_GAIN_DPS = 260.0   # deg/s per Newton thrust
    PROP_WRAP = 360000.0    # harus sinkron dengan NetworkIMU.PROP_WRAP_PERIOD
    MAX_CATCHUP_S = 0.1     # batas langkah simulasi per tick jika UI tersendat

    def __init__(self, seed=None, initial_mode="sim"):
        super().__init__()
        self.setWindowTitle("Balancing Propeller")
        self.sim = SimBackend(seed=seed)
        self.hw = HardwareBackend()
        self.be = self.sim          # backend aktif (sim / hw)
        self.mode = "sim"
        self._last_rec_msg = ""
        self.paused = False
        self.pid_locked = True     # gain PID terkunci agar tidak tergeser tak sengaja

        # buffer grafik (pendek, hanya jendela WINDOW_S) dan buffer event
        # (panjang, seluruh respons sejak event) dipisah supaya metrik
        # tidak rusak saat data lama terbuang.
        plot_len = int(self.WINDOW_S * 1000 / self.TICK_MS * 1.25)
        self.hist = collections.deque(maxlen=plot_len)
        self.ev_buf = []
        self.ev_max = int(self.EVENT_MAX_S * 1000 / self.TICK_MS)

        self.frame = 0
        self.event = None          # (kind, t0)
        self.pend = None           # event yang menunggu debounce
        self._last_metrics = None
        self._conn_state = None
        self._t_last = None        # perf_counter tick terakhir
        self._acc = 0.0            # akumulator waktu nyata (detik)
        self._ylim = None

        self.debounce = QtCore.QTimer(self, singleShot=True)
        self.debounce.timeout.connect(self._commit_event)

        self.stream = TelemetryStream(on_impulse=self.trigger_impulse)
        self.stream.extra = {"mode": "sim"}
        self.prop1_rot = 0.0
        self.prop2_rot = 0.0

        self.scn = None            # state skenario yang sedang berjalan
        self.scn_queue = []

        root = QtWidgets.QWidget()
        rv = QtWidgets.QVBoxLayout(root)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(0)
        rv.addWidget(self._build_header())

        body = QtWidgets.QWidget()
        bl = QtWidgets.QHBoxLayout(body)
        bl.setContentsMargins(14, 12, 14, 14)
        bl.setSpacing(0)
        split = QtWidgets.QSplitter(Qt.Horizontal)
        split.addWidget(self._build_left())
        split.addWidget(self._build_panel())
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 0)
        split.setChildrenCollapsible(False)
        split.setSizes([1000, 380])
        bl.addWidget(split)
        rv.addWidget(body, 1)
        self.setCentralWidget(root)

        self._build_shortcuts()
        self._refresh_step_btn()
        self._apply_pid_lock()
        self._apply_initial_mode(initial_mode)

        self.timer = QtCore.QTimer(self)
        self.timer.setTimerType(Qt.PreciseTimer)
        self.timer.timeout.connect(self.tick)
        self.timer.start(self.TICK_MS)

    # ------------------------------------------------------------------
    # ukuran jendela menyesuaikan layar
    # ------------------------------------------------------------------
    def show_fitted(self):
        screen = self.screen() or QtGui.QGuiApplication.primaryScreen()
        avail = screen.availableGeometry()
        want_w, want_h = 1460, 900
        if avail.width() < want_w or avail.height() < want_h:
            self.showMaximized()
        else:
            self.resize(want_w, want_h)
            self.move(avail.center() - self.rect().center())
            self.show()

    def closeEvent(self, event):
        self.hw.stop_recording()
        self.hw.disconnect()
        self.stream.close()
        super().closeEvent(event)

    # ------------------------------------------------------------------
    # HEADER
    # ------------------------------------------------------------------
    def _build_header(self):
        hdr = QtWidgets.QFrame()
        hdr.setObjectName("Header")
        hdr.setFixedHeight(54)
        hl = QtWidgets.QHBoxLayout(hdr)
        hl.setContentsMargins(18, 8, 18, 8)
        hl.setSpacing(10)

        logo = QtWidgets.QLabel("P")
        logo.setObjectName("Logo")
        logo.setFixedSize(30, 30)
        logo.setAlignment(Qt.AlignCenter)

        title = QtWidgets.QLabel("Balancing Propeller")
        title.setObjectName("AppTitle")

        group = QtWidgets.QLabel(GROUP_NAME)
        group.setObjectName("GroupTag")

        course = QtWidgets.QLabel("PSKD \u00b7 Praktikum Sistem Kontrol Dasar")
        course.setObjectName("AppSub")
        course.setMinimumWidth(0)
        course.setSizePolicy(QtWidgets.QSizePolicy.Ignored,
                             QtWidgets.QSizePolicy.Preferred)

        sep = QtWidgets.QFrame()
        sep.setFixedSize(1, 22)
        sep.setStyleSheet(f"background: {BORDER};")

        names = QtWidgets.QLabel("  \u00b7  ".join(n for n, _ in MEMBERS))
        names.setObjectName("GroupNames")
        names.setToolTip("\n".join(f"{i}. {n}  \u2014  {nim}"
                                   for i, (n, nim) in enumerate(MEMBERS, 1)))
        names.setMinimumWidth(0)
        names.setSizePolicy(QtWidgets.QSizePolicy.Ignored,
                            QtWidgets.QSizePolicy.Preferred)

        hl.addWidget(logo)
        hl.addWidget(title)
        hl.addWidget(group)
        hl.addSpacing(4)
        hl.addWidget(course, 1)
        hl.addWidget(sep)
        hl.addWidget(names, 2)

        pill = QtWidgets.QFrame()
        pill.setObjectName("Pill")
        pl = QtWidgets.QHBoxLayout(pill)
        pl.setContentsMargins(11, 5, 13, 5)
        pl.setSpacing(6)
        self.pill_dot = QtWidgets.QLabel("\u25cf")
        self.pill_dot.setObjectName("PillDot")
        host, port = self.stream.addr
        self.pill_txt = QtWidgets.QLabel("PROCESSING  \u00b7  connecting\u2026")
        self.pill_txt.setObjectName("PillText")
        pill.setToolTip(f"UDP {host}:{port}\n"
                        "Status berdasarkan balasan ACK dari BalancingPropellerIMU.pde.\n"
                        "Hijau = Processing benar-benar menerima data.")
        pl.addWidget(self.pill_dot)
        pl.addWidget(self.pill_txt)
        hl.addWidget(pill)

        wrap = QtWidgets.QWidget()
        wv = QtWidgets.QVBoxLayout(wrap)
        wv.setContentsMargins(0, 0, 0, 0)
        wv.setSpacing(0)
        wv.addWidget(hdr)
        strip = QtWidgets.QFrame()
        strip.setFixedHeight(3)
        strip.setStyleSheet(f"background: {ACCENT};")
        wv.addWidget(strip)
        return wrap

    # ------------------------------------------------------------------
    # util grafik
    # ------------------------------------------------------------------
    def _style_plot(self, pl):
        for ax in ("left", "bottom"):
            pl.getAxis(ax).setPen(pg.mkPen("#D8DEE7"))
            pl.getAxis(ax).setTextPen(pg.mkPen(MUTED))
        pl.hideButtons()
        pl.setMenuEnabled(False)
        pl.showGrid(x=True, y=True, alpha=0.15)

    def _make_event_marker(self, plot):
        """InfiniteLine vertikal yang menandai saat setpoint/beban berubah."""
        line = pg.InfiniteLine(angle=90, movable=False,
                               pen=pg.mkPen(AMBER, width=1.2, style=Qt.DashLine))
        line.setVisible(False)
        plot.addItem(line)
        return line

    @staticmethod
    def _make_legend(plot):
        leg = plot.addLegend(offset=(12, 8), labelTextSize="8pt")
        leg.setBrush(pg.mkBrush(255, 255, 255, 225))
        leg.setPen(pg.mkPen(BORDER))
        return leg

    @staticmethod
    def _curve(plot, **kw):
        c = plot.plot(**kw)
        c.setDownsampling(auto=True, method="peak")
        c.setClipToView(True)
        return c

    @staticmethod
    def _make_table(headers, stretch_col=None):
        tbl = QtWidgets.QTableWidget(0, len(headers))
        tbl.setHorizontalHeaderLabels(headers)
        tbl.verticalHeader().setVisible(False)
        tbl.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        tbl.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        tbl.setAlternatingRowColors(True)
        tbl.setShowGrid(False)
        hh = tbl.horizontalHeader()
        hh.setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        if stretch_col is not None:
            hh.setSectionResizeMode(stretch_col, QtWidgets.QHeaderView.ResizeToContents)
        return tbl

    @staticmethod
    def _append_row(tbl, values):
        row = tbl.rowCount()
        tbl.insertRow(row)
        for col, val in enumerate(values):
            item = QtWidgets.QTableWidgetItem(val)
            if col > 0:
                item.setTextAlignment(Qt.AlignCenter)
            tbl.setItem(row, col, item)
        tbl.scrollToBottom()

    # ------------------------------------------------------------------
    # KOLOM KIRI: animasi + tab telemetri / log / skenario
    # ------------------------------------------------------------------
    def _build_left(self):
        pg.setConfigOptions(antialias=False, background=PLOT_BG, foreground=MUTED)

        self.view = BeamView()
        self.view.impulse_requested.connect(self.trigger_impulse)
        self.view.setMinimumHeight(240)
        self.view.Fmax, self.view.L = self.be.p.Fmax, self.be.p.L
        self.view.LIMIT_DEG = math.degrees(self.be.p.stop)
        lim = self.view.LIMIT_DEG

        # ---------- Tab: Response (angle + PID output) ----------
        self.p1 = pg.PlotWidget(background=PLOT_BG)
        self.p1.setLabel("left", "Angle \u03b8", "\u00b0")
        self._make_legend(self.p1)
        self.c_meas = self._curve(self.p1, pen=pg.mkPen("#9AA3AF", width=1), name="IMU")
        self.c_th = self._curve(self.p1, pen=pg.mkPen(ACCENT, width=2), name="\u03b8 actual")
        self.c_sp = self._curve(self.p1, pen=pg.mkPen(ACCENT, width=1.6, style=Qt.DashLine),
                                name="Setpoint")
        # garis batas mekanik
        for y in (-lim, lim):
            self.p1.addLine(y=y, pen=pg.mkPen(RED, width=1, style=Qt.DotLine))
        # band toleransi settling
        self.band = pg.LinearRegionItem(values=(0, 0), orientation="horizontal",
                                        movable=False,
                                        brush=pg.mkBrush(47, 111, 237, 25),
                                        pen=pg.mkPen(ACCENT, width=0))
        self.band.setZValue(-10)
        self.band.setVisible(False)
        self.p1.addItem(self.band)
        self._set_angle_range(25)

        self.p2 = pg.PlotWidget(background=PLOT_BG)
        self.p2.setLabel("left", "PID output u", "%")
        self.p2.setLabel("bottom", "Time", "s")
        self.p2.setYRange(-110, 110)
        self.p2.setXLink(self.p1)
        self.c_u = self._curve(self.p2, pen=pg.mkPen(GREEN, width=1.8))

        # ---------- Tab: PID term breakdown ----------
        self.p3 = pg.PlotWidget(background=PLOT_BG)
        self.p3.setLabel("left", "Kontribusi", "%")
        self.p3.setLabel("bottom", "Time", "s")
        self.p3.setYRange(-110, 110)
        self.p3.setXLink(self.p1)
        self._make_legend(self.p3)
        self.c_pt = self._curve(self.p3, pen=pg.mkPen(ACCENT, width=1.8), name="P")
        self.c_it = self._curve(self.p3, pen=pg.mkPen(GREEN, width=1.8), name="I")
        self.c_dt = self._curve(self.p3, pen=pg.mkPen(PURPLE, width=1.8), name="D")
        self.c_ut = self._curve(self.p3, pen=pg.mkPen("#8A94A3", width=1.4, style=Qt.DashLine),
                                name="u total")

        # ---------- Tab: Error & kecepatan sudut ----------
        self.p4 = pg.PlotWidget(background=PLOT_BG)
        self.p4.setLabel("left", "Error e = sp \u2212 \u03b8", "\u00b0")
        self.p4.addLine(y=0, pen=pg.mkPen("#B7BFC9", width=1))
        self.p4.setXLink(self.p1)
        self.c_err = self._curve(self.p4, pen=pg.mkPen(RED, width=1.8))

        self.p5 = pg.PlotWidget(background=PLOT_BG)
        self.p5.setLabel("left", "\u03c9", "\u00b0/s")
        self.p5.setLabel("bottom", "Time", "s")
        self.p5.setXLink(self.p1)
        self.c_omega = self._curve(self.p5, pen=pg.mkPen(PURPLE, width=1.8))

        for pl in (self.p1, self.p2, self.p3, self.p4, self.p5):
            self._style_plot(pl)
        self.event_markers = [self._make_event_marker(pl)
                              for pl in (self.p1, self.p2, self.p3, self.p4, self.p5)]

        def stack(*widgets):
            w = QtWidgets.QWidget()
            lay = QtWidgets.QVBoxLayout(w)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.setSpacing(6)
            for x in widgets:
                lay.addWidget(x, 1)
            return w

        tabs = QtWidgets.QTabWidget()
        tabs.setDocumentMode(True)
        tabs.addTab(stack(self.p1, self.p2), "Response")
        tabs.addTab(stack(self.p3), "PID Terms")
        tabs.addTab(stack(self.p4, self.p5), "Error && \u03c9")
        tabs.addTab(self._build_tuning_log_tab(), "Tuning Log")
        tabs.addTab(self._build_scenario_tab(), "Skenario Otomatis")
        self.tabs = tabs

        telemetry = Card("Telemetry")
        telemetry.body.addWidget(tabs, 1)

        left = QtWidgets.QSplitter(Qt.Vertical)
        left.addWidget(self.view)
        left.addWidget(telemetry)
        left.setSizes([380, 440])
        left.setStretchFactor(0, 4)
        left.setStretchFactor(1, 6)
        left.setChildrenCollapsible(False)
        return left

    # ---- tab riwayat tuning ----
    def _build_tuning_log_tab(self):
        w = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(w)
        lay.setContentsMargins(6, 8, 6, 6)
        lay.setSpacing(8)

        info = QtWidgets.QLabel("Simpan gain Kp/Ki/Kd saat ini beserta metrik respons "
                                "terakhir untuk membandingkan hasil tuning.")
        info.setObjectName("EventLabel")
        info.setWordWrap(True)
        lay.addWidget(info)

        self.tuning_table = self._make_table(
            ["t", "Kp", "Ki", "Kd", "Event", "Mp", "tr", "ts", "ess"], stretch_col=4)
        lay.addWidget(self.tuning_table, 1)

        row = QtWidgets.QHBoxLayout()
        row.setSpacing(7)
        b_log = QtWidgets.QPushButton("\u2795  Catat gain saat ini")
        b_log.setObjectName("Primary")
        b_log.setToolTip("Simpan Kp/Ki/Kd saat ini + metrik respons terakhir (Ctrl+L)")
        b_log.clicked.connect(self.log_tuning)
        b_clear = QtWidgets.QPushButton("Bersihkan")
        b_clear.clicked.connect(lambda: self.tuning_table.setRowCount(0))
        row.addStretch(1)
        row.addWidget(b_clear)
        row.addWidget(b_log)
        lay.addLayout(row)
        return w

    # ---- tab skenario uji otomatis ----
    def _build_scenario_tab(self):
        w = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(w)
        lay.setContentsMargins(6, 8, 6, 6)
        lay.setSpacing(8)

        top = QtWidgets.QHBoxLayout()
        top.setSpacing(7)
        self.scenario_status = QtWidgets.QLabel(
            f"Belum dijalankan  \u00b7  {len(SCENARIOS)} skenario, masing-masing "
            f"{SCN_SETTLE_S:.0f} s settle + {SCN_MEASURE_S:.0f} s ukur (waktu simulasi)")
        self.scenario_status.setObjectName("EventLabel")
        self.scenario_status.setWordWrap(True)
        self.btn_scn_run = QtWidgets.QPushButton("\u25b6  Jalankan semua")
        self.btn_scn_run.setObjectName("Primary")
        self.btn_scn_run.setToolTip("Jalankan semua skenario (F5)")
        self.btn_scn_run.clicked.connect(self.run_scenarios)
        self.btn_scn_stop = QtWidgets.QPushButton("Stop")
        self.btn_scn_stop.setObjectName("Danger")
        self.btn_scn_stop.setToolTip("Hentikan skenario (Esc)")
        self.btn_scn_stop.setEnabled(False)
        self.btn_scn_stop.clicked.connect(lambda: self.stop_scenarios("Dihentikan"))
        top.addWidget(self.scenario_status, 1)
        top.addWidget(self.btn_scn_stop)
        top.addWidget(self.btn_scn_run)
        lay.addLayout(top)

        self.scenario_table = self._make_table(
            ["Skenario", "Kp / Ki / Kd", "Mp", "tr", "tp", "ts", "ess", "Deviasi"],
            stretch_col=0)
        lay.addWidget(self.scenario_table, 1)
        return w

    # ------------------------------------------------------------------
    # PANEL KANAN: kontrol
    # ------------------------------------------------------------------
    def _build_panel(self):
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setMinimumWidth(340)
        scroll.setMaximumWidth(560)

        panel = QtWidgets.QWidget()
        pv = QtWidgets.QVBoxLayout(panel)
        pv.setContentsMargins(10, 0, 4, 0)
        pv.setSpacing(10)

        pv.addWidget(self._build_source_card())

        controller = Card("PID")
        # Tombol gembok di header kartu: kunci/buka slider gain PID.
        self.btn_pid_lock = QtWidgets.QPushButton()
        self.btn_pid_lock.setObjectName("Lock")
        self.btn_pid_lock.setCheckable(True)
        self.btn_pid_lock.setChecked(True)
        self.btn_pid_lock.setFixedWidth(34)
        self.btn_pid_lock.clicked.connect(self.toggle_pid_lock)
        controller.head.addWidget(self.btn_pid_lock)
        # Rentang slider disesuaikan dengan model terukur (docs/ringkasan_pengukuran.md):
        # di atas kira-kira Kp > 0.2 + 11.4*Kd sistem tidak stabil.
        self.kp = Param("Kp", 0, 5, self.be.kp, 0.05, "%/\u00b0")
        self.ki = Param("Ki", 0, 3, self.be.ki, 0.05, "%/(\u00b0\u00b7s)")
        self.kd = Param("Kd", 0, 1.5, self.be.kd, 0.05, "%/(\u00b0/s)")
        self.kp.setToolTip("Gain proporsional: u_P = Kp \u00b7 e\n"
                           "Batas stabil kira-kira Kp < 0.2 + 11.4\u00b7Kd")
        self.ki.setToolTip("Gain integral: u_I = Ki \u00b7 \u222be dt (dengan anti-windup)")
        self.kd.setToolTip("Gain derivatif: u_D = \u2212Kd \u00b7 d\u03b8/dt (D pada pengukuran, filter 20 ms)")
        for w in (self.kp, self.ki, self.kd):
            controller.body.addWidget(w)
            w.changed.connect(self.on_gains)
        pv.addWidget(controller)

        ref = Card("Input", accent=ACCENT)
        self.sp = Param("Setpoint", -SP_LIMIT, SP_LIMIT, 0, 1, "\u00b0", 1)
        self.lm = Param("Load mass", 0, 500, 0, 10, "g", 0)
        self.lx = Param("Load position", 5, 15, 10, 1, "cm", 1)
        self.nz = Param("Noise (\u03c3)", 0, 2, self.be.noise, 0.05, "\u00b0")
        self.lx.setToolTip("Jarak beban dari poros (5 \u2013 15 cm, sisi kiri)")
        self.nz.setToolTip("Standar deviasi noise sensor IMU")
        self.sp.changed.connect(self.on_sp)
        self.lm.changed.connect(self.on_load)
        self.lx.changed.connect(self.on_load)
        self.nz.changed.connect(lambda v: setattr(self.be, "noise", v))
        for w in (self.sp, self.lm, self.lx, self.nz):
            ref.body.addWidget(w)
        pv.addWidget(ref)

        metrics = Card("Performa Respons")
        self.mt_event = QtWidgets.QLabel("Waiting for setpoint / load change")
        self.mt_event.setObjectName("EventLabel")
        self.mt_event.setWordWrap(True)
        metrics.body.addWidget(self.mt_event)

        mg = QtWidgets.QGridLayout()
        mg.setSpacing(7)
        self.metric_w = {}
        for i, key in enumerate(METRIC_KEYS):
            m = Metric(METRIC_TITLES[key], METRIC_COLORS[key], tooltip=METRIC_TIPS[key])
            self.metric_w[key] = m
            mg.addWidget(m, i // 2, i % 2)
        metrics.body.addLayout(mg)
        pv.addWidget(metrics)

        grid = QtWidgets.QGridLayout()
        grid.setSpacing(7)
        self.btn_pause = QtWidgets.QPushButton("\u23f8  Pause")
        self.btn_pause.setObjectName("Primary")
        self.btn_pause.setToolTip("Pause / lanjutkan simulasi (Space)")
        self.btn_pause.clicked.connect(self.toggle_pause)
        b_reset = QtWidgets.QPushButton("\u21ba  Reset")
        b_reset.setObjectName("Danger")
        b_reset.setToolTip("Reset simulasi, setpoint & beban ke default (Ctrl+R).\n"
                           "Gain PID dan noise tidak diubah.")
        b_reset.clicked.connect(self.reset)
        b_int = QtWidgets.QPushButton("Reset Integral")
        b_int.setToolTip("Kosongkan akumulator integral PID (Ctrl+I)")
        b_int.clicked.connect(lambda: self.be.reset_integral())
        self.btn_step = QtWidgets.QPushButton(f"+{SP_STEP:.0f}\u00b0 Setpoint")
        self.btn_step.setObjectName("Warning")
        self.btn_step.setToolTip(f"Naikkan setpoint {SP_STEP:.0f}\u00b0 "
                                 f"(maks {SP_LIMIT:.0f}\u00b0)  (Ctrl+\u2191)")
        self.btn_step.clicked.connect(self.step_sp)

        self.btn_disturb = QtWidgets.QPushButton("💥  Sentak Gangguan (Impuls)")
        self.btn_disturb.setToolTip("Beri sentakan gangguan torsi mendadak pada batang (Tombol D / Space di Processing)")
        self.btn_disturb.clicked.connect(lambda: self.trigger_impulse(2.5))

        grid.addWidget(self.btn_pause, 0, 0)
        grid.addWidget(b_reset, 0, 1)
        grid.addWidget(b_int, 1, 0)
        grid.addWidget(self.btn_step, 1, 1)
        grid.addWidget(self.btn_disturb, 2, 0, 1, 2)
        pv.addLayout(grid)

        pv.addStretch(1)
        scroll.setWidget(panel)
        # lebar minimum mengikuti isi panel supaya tidak ada yang terpotong
        sb_w = scroll.verticalScrollBar().sizeHint().width()
        scroll.setMinimumWidth(max(340, panel.minimumSizeHint().width() + sb_w + 4))
        return scroll

    # ------------------------------------------------------------------
    # SUMBER DATA: simulasi / hardware (Arduino Uno, firmware kating)
    #   Mode hardware = BACA SAJA: tidak ada data yang dikirim ke Uno.
    # ------------------------------------------------------------------
    def _build_source_card(self):
        card = Card("Sumber Data", accent=PURPLE)

        self.cb_mode = QtWidgets.QComboBox()
        self.cb_mode.addItem("Simulasi", "sim")
        self.cb_mode.addItem("Hardware (Arduino Uno \u00b7 baca saja)", "hw")
        self.cb_mode.currentIndexChanged.connect(
            lambda _: self.set_mode(self.cb_mode.currentData()))
        card.body.addWidget(self.cb_mode)

        self.hw_box = QtWidgets.QWidget()
        g = QtWidgets.QGridLayout(self.hw_box)
        g.setContentsMargins(0, 0, 0, 0)
        g.setHorizontalSpacing(6)
        g.setVerticalSpacing(6)
        row = 0

        # --- port ---
        self.cb_port = QtWidgets.QComboBox()
        self.cb_port.setMinimumWidth(0)
        self.cb_port.setSizeAdjustPolicy(
            QtWidgets.QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.cb_port.setToolTip("Port USB (Arduino) ditaruh paling atas,\n"
                                "port Bluetooth di bawah.")
        b_refresh = QtWidgets.QPushButton("\u21bb")
        b_refresh.setToolTip("Scan ulang port COM")
        b_refresh.setFixedWidth(34)
        b_refresh.clicked.connect(self._refresh_ports)
        self.btn_conn = QtWidgets.QPushButton("Connect")
        self.btn_conn.setObjectName("Primary")
        self.btn_conn.clicked.connect(self._toggle_connect)
        g.addWidget(QtWidgets.QLabel("Port"), row, 0)
        g.addWidget(self.cb_port, row, 1)
        g.addWidget(b_refresh, row, 2)
        g.addWidget(self.btn_conn, row, 3)
        row += 1

        # --- arah sudut (sudut selalu kolom f2 dari Uno) ---
        self.chk_inv = QtWidgets.QCheckBox("Balik arah sudut")
        self.chk_inv.setToolTip("Centang jika arah miring di layar berlawanan\n"
                                "dengan arah miring batang asli.")
        self.chk_inv.toggled.connect(self._on_mapping)
        g.addWidget(self.chk_inv, row, 0, 1, 4)
        row += 1

        b_tare = QtWidgets.QPushButton("Nol-kan (0\u00b0)")
        b_tare.setToolTip("Jadikan posisi batang sekarang sebagai 0\u00b0.\n"
                          "Tahan batang dalam posisi datar dulu.")
        b_tare.clicked.connect(self._tare)
        b_untare = QtWidgets.QPushButton("Hapus offset")
        b_untare.clicked.connect(self._untare)
        g.addWidget(b_tare, row, 0, 1, 2)
        g.addWidget(b_untare, row, 2, 1, 2)
        row += 1

        self.hw_status = QtWidgets.QLabel()
        self.hw_status.setObjectName("EventLabel")
        self.hw_status.setWordWrap(True)
        g.addWidget(self.hw_status, row, 0, 1, 4)
        row += 1

        # --- beban fisik ---
        self.chk_load = QtWidgets.QCheckBox("Beban fisik terpasang")
        self.chk_load.setToolTip("Isi massa & posisi beban yang BENAR-BENAR dipasang\n"
                                 "di batang. Hanya dicatat ke CSV & ditampilkan;\n"
                                 "tidak mempengaruhi alat.")
        self.chk_load.toggled.connect(self._on_hw_load)
        g.addWidget(self.chk_load, row, 0, 1, 4)
        row += 1

        # --- perekaman ---
        self.ed_label = QtWidgets.QLineEdit()
        self.ed_label.setPlaceholderText("Label percobaan, mis. diam_kiri")
        self.btn_rec = QtWidgets.QPushButton("\u25cf  Rekam")
        self.btn_rec.setObjectName("Danger")
        self.btn_rec.setToolTip("Simpan SEMUA baris data Uno ke CSV di folder data/")
        self.btn_rec.clicked.connect(self._toggle_record)
        g.addWidget(self.ed_label, row, 0, 1, 3)
        g.addWidget(self.btn_rec, row, 3)
        row += 1

        self.rec_status = QtWidgets.QLabel()
        self.rec_status.setObjectName("EventLabel")
        self.rec_status.setWordWrap(True)
        self.rec_status.setTextInteractionFlags(Qt.TextSelectableByMouse)
        b_folder = QtWidgets.QPushButton("Buka folder data")
        b_folder.clicked.connect(self._open_data_dir)
        g.addWidget(self.rec_status, row, 0, 1, 3)
        g.addWidget(b_folder, row, 3)
        row += 1

        g.setColumnStretch(1, 1)
        card.body.addWidget(self.hw_box)
        self.hw_box.setVisible(False)

        self.hw_timer = QtCore.QTimer(self)
        self.hw_timer.timeout.connect(self._update_hw_status)
        self.hw_timer.start(200)
        self._refresh_ports()
        self._update_hw_status()
        return card

    def _refresh_ports(self):
        cur = self.cb_port.currentData()
        self.cb_port.clear()
        for dev, desc in list_ports():
            self.cb_port.addItem(desc, dev)
        if self.cb_port.count() == 0:
            self.cb_port.addItem("(tidak ada port)", None)
        i = self.cb_port.findData(cur)
        if i >= 0:
            self.cb_port.setCurrentIndex(i)

    def _toggle_connect(self):
        if self.hw.is_open:
            if self.hw.recording:
                self._toggle_record()
            self.hw.disconnect()
        else:
            port = self.cb_port.currentData()
            if not port:
                self.hw.error = "Pilih port COM dulu (colok Uno, lalu \u21bb)."
            else:
                try:
                    self.hw.connect(port)
                    self.reset()
                except Exception as exc:
                    self.hw.error = f"Gagal membuka {port}: {exc}"
        self._update_hw_status()

    def _on_mapping(self, *_):
        self.hw.set_invert(self.chk_inv.isChecked())
        self.hist.clear()
        self._clear_event()

    def _tare(self):
        self.hw.tare()
        self.hist.clear()
        self._clear_event()

    def _untare(self):
        self.hw.offset = 0.0
        self.hist.clear()
        self._clear_event()

    def _on_hw_load(self, *_):
        if self.mode != "hw":
            return
        if self.chk_load.isChecked():
            self.hw.set_load(self.lm.value() / 1000.0, self.lx.value() / 100.0)
        else:
            self.hw.set_load(0.0, self.lx.value() / 100.0)

    def _toggle_record(self):
        if self.hw.recording:
            path, rows = self.hw.rec_path, self.hw.rec_rows
            self.hw.stop_recording()
            self._last_rec_msg = f"Tersimpan: {os.path.basename(path)}  ({rows} baris)"
        else:
            if not self.hw.receiving:
                self._last_rec_msg = "\u26a0 Belum ada data dari Uno, rekaman tidak dimulai."
            else:
                path = self.hw.start_recording(self.ed_label.text())
                self._last_rec_msg = ""
        self._update_hw_status()

    def _open_data_dir(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(DATA_DIR))

    def _update_hw_status(self):
        hw = self.hw
        self.btn_conn.setText("Disconnect" if hw.is_open else "Connect")
        if not HAVE_SERIAL:
            state = "pyserial belum terpasang \u2192 pip install pyserial"
        elif not hw.is_open:
            state = "Tidak terhubung"
        elif hw.receiving:
            raw = hw.raw_angle()
            raw_s = "\u2014" if raw is None else f"{raw:+.2f}\u00b0"
            state = (f"\u25cf Data masuk {hw.rate_hz:.0f} Hz dari {hw.port}  \u00b7  "
                     f"sudut Uno {raw_s}  \u00b7  offset {hw.offset:+.2f}\u00b0")
        else:
            state = (f"{hw.port} terbuka, menunggu data\u2026  (Uno reset & "
                     "menyiapkan ESC \u00b17 s setiap port dibuka)")
        if hw.bad_lines:
            state += f"\nBaris rusak: {hw.bad_lines}"
        if hw.other_lines:
            state += f"\nPesan Uno: {hw.other_lines[-1]}"
        if hw.error:
            state += f"\n\u26a0 {hw.error}"
        self.hw_status.setText(state)

        # status rekam
        if hw.recording:
            self.btn_rec.setText("\u25a0  Stop")
            self.ed_label.setEnabled(False)
            self.rec_status.setText(
                f"\u25cf MEREKAM  {hw.rec_duration:5.1f} s  \u00b7  {hw.rec_rows} baris\n"
                f"{os.path.basename(hw.rec_path)}")
            self.rec_status.setStyleSheet(f"color: {RED};")
        else:
            self.btn_rec.setText("\u25cf  Rekam")
            self.ed_label.setEnabled(True)
            self.rec_status.setText(self._last_rec_msg or "Tidak merekam")
            self.rec_status.setStyleSheet("")

        # data tambahan untuk Processing
        self.stream.extra = {
            "mode": self.mode,
            "conn": int(hw.receiving) if self.mode == "hw" else 1,
            "port": hw.port or "",
            "inv": int(hw.invert),
            "off": round(hw.offset, 2),
            "rate": round(hw.rate_hz, 1),
            "rec": int(hw.recording),
            "lbl": hw.rec_label if hw.recording else "",
        } if self.mode == "hw" else {"mode": "sim"}

    def _apply_initial_mode(self, mode):
        """Pilih mode awal (dari launcher) dan, untuk hardware, port yang
        terlihat seperti Arduino/USB tanpa campur tangan pengguna."""
        if mode == "hw":
            i = self.cb_mode.findData("hw")
            if i >= 0:
                self.cb_mode.setCurrentIndex(i)
            for k in range(self.cb_port.count()):
                text = self.cb_port.itemText(k).lower()
                if any(s in text for s in ("arduino", "ch340", "usb serial", "usb-serial")):
                    self.cb_port.setCurrentIndex(k)
                    break
            else:
                self.cb_port.insertItem(0, "(pilih port Uno \u2014 colok USB lalu \u21bb)", None)
                self.cb_port.setCurrentIndex(0)
        else:
            i = self.cb_mode.findData("sim")
            if i >= 0:
                self.cb_mode.setCurrentIndex(i)

    def set_mode(self, mode):
        if mode == self.mode:
            return
        self.stop_scenarios("Dihentikan (ganti sumber data)" if self.scn else None)
        if mode != "hw" and self.hw.recording:
            self._toggle_record()
        self.mode = mode
        hw = mode == "hw"
        self.be = self.hw if hw else self.sim
        self.be.set_gains(self.kp.value(), self.ki.value(), self.kd.value())
        self.hw_box.setVisible(hw)
        # Mode hardware: PID, setpoint, noise, impuls & skenario tidak berlaku
        # (motor dikendalikan firmware kating). Slider beban tetap aktif
        # sebagai keterangan beban fisik.
        for w in (self.sp, self.nz, self.btn_disturb,
                  self.btn_scn_run, self.btn_step):
            w.setEnabled(not hw)
        # Gain PID mengikuti status gembok (dan terkunci paksa saat mode HW).
        self._apply_pid_lock()
        self.btn_pid_lock.setEnabled(not hw)
        tip = ("Mode hardware: dikendalikan firmware Uno (kating).\n"
               "GUI hanya membaca data.") if hw else ""
        self.sp.setToolTip(tip)
        self.view.setToolTip("" if hw else
                             "Klik pada sisi kiri atau kanan batang untuk "
                             "memberi sentakan gangguan (Impuls)!")
        self.reset()
        if hw:
            self._on_hw_load()
        else:
            self._refresh_step_btn()
            self.be.set_load(self.lm.value() / 1000.0, self.lx.value() / 100.0)
        self._update_hw_status()

    def _build_shortcuts(self):
        def sc(key, fn):
            s = QtGui.QShortcut(QtGui.QKeySequence(key), self)
            s.setContext(Qt.WindowShortcut)
            s.activated.connect(fn)

        sc(Qt.Key_Space, self.toggle_pause)
        sc("D", lambda: self.trigger_impulse(2.5))
        sc("Shift+D", lambda: self.trigger_impulse(-2.5))
        sc("Ctrl+R", self.reset)
        sc("Ctrl+I", lambda: self.be.reset_integral())
        sc("Ctrl+Up", self.step_sp)
        sc("Ctrl+L", self.log_tuning)
        sc("F5", self.run_scenarios)
        sc("Esc", lambda: self.stop_scenarios("Dihentikan") if self.scn else None)

    def trigger_impulse(self, delta_w=2.5):
        """Beri gangguan impuls torsi pada batang dan catat metrik respons."""
        if self.mode == "hw":
            return               # tidak berlaku pada alat asli
        self.be.apply_impulse(delta_w)
        self._set_event("load", self.be.t)

    # ------------------------------------------------------------------
    # HANDLER INPUT
    # ------------------------------------------------------------------
    def toggle_pid_lock(self):
        """Kunci/buka gain PID. Saat terkunci slider & spinbox dinonaktifkan
        agar parameter tidak tergeser tanpa sengaja."""
        self.pid_locked = self.btn_pid_lock.isChecked()
        self._apply_pid_lock()

    def _apply_pid_lock(self):
        # Mode hardware memang sudah menonaktifkan PID; lock tetap dihormati
        # supaya saat kembali ke simulasi status kunci tidak "bocor".
        hw = self.mode == "hw"
        for w in (self.kp, self.ki, self.kd):
            w.set_locked(self.pid_locked or hw)
        self.btn_pid_lock.setText("\U0001f512" if self.pid_locked else "\U0001f513")
        self.btn_pid_lock.setToolTip(
            "Gain PID terkunci \u2014 klik untuk membuka."
            if self.pid_locked else
            "Gain PID terbuka \u2014 klik untuk mengunci.")

    def on_gains(self, _=None):
        self.be.set_gains(self.kp.value(), self.ki.value(), self.kd.value())

    def _start_pending(self, kind):
        if self.pend is None or self.pend["kind"] != kind:
            self.pend = dict(kind=kind, t0=self.be.t)
        self.debounce.start(350)

    def on_sp(self, v):
        if self.scn:
            self.stop_scenarios("Dihentikan (setpoint diubah manual)")
        self._start_pending("sp")
        self.be.set_setpoint(v)
        self._refresh_step_btn()

    def on_load(self, _=None):
        if self.scn:
            self.stop_scenarios("Dihentikan (beban diubah manual)")
        self._start_pending("load")
        if self.mode == "hw":
            self._on_hw_load()      # hanya keterangan beban fisik
            return
        self.be.set_load(self.lm.value() / 1000.0, self.lx.value() / 100.0)

    def _commit_event(self):
        if self.pend:
            self._set_event(self.pend["kind"], self.pend["t0"])
            self.pend = None

    def _set_event(self, kind, t0):
        """Mulai event baru: data sejak t0 diambil dari buffer grafik, lalu
        terus ditambah di tick() ke buffer event (tidak terbuang)."""
        self.event = (kind, t0)
        self.ev_buf = [s for s in self.hist if s[COL_T] >= t0 - 1e-9]
        self._last_metrics = None
        for line in self.event_markers:
            line.setPos(t0)
            line.setVisible(True)

    def _clear_event(self):
        self.event = None
        self.pend = None
        self.debounce.stop()
        self.ev_buf = []
        self._last_metrics = None
        self.band.setVisible(False)
        for line in self.event_markers:
            line.setVisible(False)
        self.mt_event.setText("Waiting for setpoint / load change")
        for m in self.metric_w.values():
            m.set(DASH)

    def _refresh_step_btn(self):
        self.btn_step.setEnabled(self.mode != "hw" and
                                 self.sp.value() < SP_LIMIT - 1e-9)

    def step_sp(self):
        if self.btn_step.isEnabled():
            self.sp.set_value(min(SP_LIMIT, self.sp.value() + SP_STEP))

    def toggle_pause(self):
        self.paused = not self.paused
        self._t_last = None
        self.btn_pause.setText("\u25b6  Continue" if self.paused else "\u23f8  Pause")

    def reset(self):
        self.stop_scenarios("Dihentikan (reset)" if self.scn else None)
        self.be.reset()
        if self.mode == "hw":
            # beban fisik tetap seperti yang diisi pengguna
            self._on_hw_load()
        else:
            # kembalikan input ke default tanpa memicu event
            for prm in (self.sp, self.lm, self.lx):
                prm.set_value_silent(prm.default)
            self.be.set_setpoint(self.sp.value())
            self.be.set_load(self.lm.value() / 1000.0, self.lx.value() / 100.0)
        self.hist.clear()
        self._clear_event()
        self.prop1_rot = self.prop2_rot = 0.0
        self.frame = 0
        self._acc = 0.0
        self._t_last = None
        self.paused = False
        self.btn_pause.setText("\u23f8  Pause")
        self._refresh_step_btn()

    # ------------------------------------------------------------------
    # LOOP UTAMA
    # ------------------------------------------------------------------
    def _prop_rate(self, thrust):
        """Kecepatan putar propeller (deg/s): idle + proporsional thrust."""
        return self.PROP_IDLE_DPS + max(0.0, thrust) * self.PROP_GAIN_DPS

    def _steps_due(self):
        """Jumlah langkah simulasi berdasarkan waktu nyata (perf_counter),
        supaya simulasi tetap real-time walau QTimer meleset."""
        now = time.perf_counter()
        if self._t_last is None:
            elapsed = self.TICK_MS / 1000.0
        else:
            elapsed = min(now - self._t_last, self.MAX_CATCHUP_S)
        self._t_last = now
        self._acc += elapsed
        n = int(self._acc / self.be.p.dt)
        self._acc -= n * self.be.p.dt
        return n

    def tick(self):
        self._update_connection_status()
        if self.paused:
            self.stream.heartbeat()
            return

        if self.mode == "hw":
            # data mengikuti IMU asli; motor belum dikendalikan -> prop diam
            s = self.be.poll()
            if s is None:
                self.stream.heartbeat()
                return
            if "conn" in self.stream.extra:
                self.stream.extra["conn"] = 1
        else:
            n = self._steps_due()
            if n == 0:
                # QTimer meleset ke bawah -> jaga status koneksi Processing
                # tetap akurat walau belum ada langkah simulasi baru.
                self.stream.heartbeat()
                return
            for _ in range(n):
                self.be.step()
            s = self.be.sample()
            dtg = n * self.be.p.dt
        self.hist.append(s)
        if self.event is not None and len(self.ev_buf) < self.ev_max:
            self.ev_buf.append(s)
        t, th, _meas, sp, _u, F1, F2 = s[:7]

        if self.mode == "sim":
            self.prop1_rot = (self.prop1_rot + self._prop_rate(F1) * dtg) % self.PROP_WRAP
            self.prop2_rot = (self.prop2_rot + self._prop_rate(F2) * dtg) % self.PROP_WRAP
        self.stream.send(th, self.prop1_rot, self.prop2_rot, sp, _u, self.be.load_m, self.be.load_x, F1, F2)

        self.view.set_state(th, sp, F1, F2, self.be.load_m, self.be.load_x,
                            self.prop1_rot, self.prop2_rot)

        self._scenario_tick()

        self.frame += 1
        if self.frame % 2:
            return

        a = np.asarray(self.hist)
        m = a[:, COL_T] > t - self.WINDOW_S
        x = a[m, COL_T]
        self.c_th.setData(x, a[m, COL_TH])
        self.c_meas.setData(x, a[m, COL_MEAS])
        self.c_sp.setData(x, a[m, COL_SP])
        self.c_u.setData(x, a[m, COL_U])
        self.c_pt.setData(x, a[m, COL_P])
        self.c_it.setData(x, a[m, COL_I])
        self.c_dt.setData(x, a[m, COL_D])
        self.c_ut.setData(x, a[m, COL_U])
        self.c_err.setData(x, a[m, COL_SP] - a[m, COL_TH])
        self.c_omega.setData(x, a[m, COL_W])
        self.p1.setXRange(t - self.WINDOW_S, t, padding=0)

        peak = float(np.max(np.abs(a[m][:, [COL_TH, COL_MEAS, COL_SP]])))
        self._set_angle_range(peak)
        self.update_metrics()

    def _set_angle_range(self, peak):
        """Sumbu Y sudut otomatis (kelipatan 5 deg, min +-25, maks +-50)
        supaya kurva tidak hilang saat batang menyentuh batas +-30 deg."""
        lim = min(50.0, max(25.0, math.ceil((peak + 3.0) / 5.0) * 5.0))
        if lim != self._ylim:
            self._ylim = lim
            self.p1.setYRange(-lim, lim, padding=0)

    CONN_LABEL = {
        "connected": ("PROCESSING  \u00b7  connected", GREEN),
        "no-ack": ("PROCESSING  \u00b7  no ACK", AMBER),
        "no-listener": ("PROCESSING  \u00b7  no listener", RED),
        "idle": ("PROCESSING  \u00b7  connecting\u2026", MUTED),
    }

    def _update_connection_status(self):
        state = self.stream.status
        if state == self._conn_state:
            return
        self._conn_state = state
        text, color = self.CONN_LABEL[state]
        self.pill_dot.setStyleSheet(f"color: {color}; font-size: 12px;")
        self.pill_txt.setText(text)

    # ------------------------------------------------------------------
    # METRIK
    # ------------------------------------------------------------------
    def _compute_current_metrics(self):
        if self.event is None or len(self.ev_buf) < 5:
            return None
        kind, t0 = self.event
        return compute_metrics(np.asarray(self.ev_buf), kind, t0, SETTLING_CRIT)

    def update_metrics(self):
        if self.event is None:
            return
        res = self._compute_current_metrics()
        if res is None:
            return
        kind, t0 = self.event
        sp_f, band = res["sp_final"], res["band"]
        self.band.setRegion((sp_f - band, sp_f + band))
        self.band.setVisible(True)

        jenis = "Setpoint step" if kind == "sp" else "Load disturbance"
        note = ""
        if len(self.ev_buf) >= self.ev_max:
            note = f"  \u00b7  (data dibatasi {self.EVENT_MAX_S:.0f} s)"
        self.mt_event.setText(f"{jenis}  \u00b7  t = {t0:.1f} s  \u00b7  "
                              f"band \u00b1{band:.2f}\u00b0{note}")
        for key, w in self.metric_w.items():
            w.set(res[key])
        self._last_metrics = res

    # ------------------------------------------------------------------
    # RIWAYAT TUNING
    # ------------------------------------------------------------------
    def log_tuning(self):
        m = self._last_metrics or {k: DASH for k in METRIC_KEYS}
        if self.event is None:
            ev = DASH
        else:
            ev = "Step setpoint" if self.event[0] == "sp" else "Gangguan beban"
        self._append_row(self.tuning_table, [
            f"{self.be.t:.1f} s", f"{self.kp.value():.2f}", f"{self.ki.value():.2f}",
            f"{self.kd.value():.2f}", ev, m["overshoot"], m["rise"],
            m["settling"], m["error"]])
        self.tabs.setCurrentIndex(3)

    # ------------------------------------------------------------------
    # SKENARIO UJI OTOMATIS (berbasis waktu simulasi)
    # ------------------------------------------------------------------
    def run_scenarios(self):
        if self.scn or self.mode == "hw":
            return
        self.scenario_table.setRowCount(0)
        self.scn_queue = list(SCENARIOS)
        self.scn_total = len(self.scn_queue)
        self.btn_scn_run.setEnabled(False)
        self.btn_scn_stop.setEnabled(True)
        if self.paused:
            self.toggle_pause()
        self.tabs.setCurrentIndex(4)
        self._start_next_scenario()

    def stop_scenarios(self, msg=None):
        self.scn = None
        self.scn_queue = []
        self.btn_scn_run.setEnabled(True)
        self.btn_scn_stop.setEnabled(False)
        if msg:
            self.scenario_status.setText(msg)

    def _apply_input(self, sp=None, load=None):
        """Set setpoint/beban ke backend + slider tanpa memicu event manual."""
        if sp is not None:
            self.sp.set_value_silent(sp)
            self.be.set_setpoint(sp)
            self._refresh_step_btn()
        if load is not None:
            mass, pos = load
            self.lm.set_value_silent(mass * 1000.0)
            self.lx.set_value_silent(pos * 100.0)
            self.be.set_load(mass, pos)

    def _start_next_scenario(self):
        if not self.scn_queue:
            self.stop_scenarios(f"Selesai  \u00b7  {self.scn_total} skenario tercatat")
            return
        name, init, change = self.scn_queue.pop(0)
        idx = self.scn_total - len(self.scn_queue)

        # kondisi awal identik untuk tiap skenario
        self._clear_event()
        self.be.reset(keep_time=True)
        sp0 = init.get("sp", 0.0)
        self._apply_input(sp=sp0, load=init.get("load", (0.0, self.lx.default / 100.0)))
        self.be.th = math.radians(sp0)
        self.be.meas = self.be.prev_meas = sp0   # hindari derivative kick

        self.scn = dict(name=name, idx=idx, change=change, phase="settle",
                        t_end=self.be.t + SCN_SETTLE_S)
        self._scenario_status()

    def _scenario_status(self):
        s = self.scn
        phase = "settle" if s["phase"] == "settle" else "mengukur"
        left = max(0.0, s["t_end"] - self.be.t)
        self.scenario_status.setText(
            f"Skenario {s['idx']}/{self.scn_total}: {s['name']}  \u00b7  "
            f"{phase} ({left:.1f} s)")

    def _scenario_tick(self):
        s = self.scn
        if s is None:
            return
        if self.frame % 10 == 0:
            self._scenario_status()
        if self.be.t < s["t_end"]:
            return

        if s["phase"] == "settle":
            kind, value = s["change"]
            t0 = self.be.t
            if kind == "sp":
                self._apply_input(sp=value)
            else:
                self._apply_input(load=value)
            self._set_event(kind, t0)
            s["phase"] = "measure"
            s["t_end"] = t0 + SCN_MEASURE_S
            self._scenario_status()
            return

        # fase ukur selesai -> catat metrik dari buffer event
        res = self._compute_current_metrics() or {k: DASH for k in METRIC_KEYS}
        gains = f"{self.kp.value():.2f} / {self.ki.value():.2f} / {self.kd.value():.2f}"
        self._append_row(self.scenario_table, [
            s["name"], gains, res["overshoot"], res["rise"], res["peak_time"],
            res["settling"], res["error"], res["deviation"]])
        self._start_next_scenario()
