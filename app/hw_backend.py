"""Backend hardware: membaca data Arduino Uno (firmware kating) lewat USB Serial.

WEEK 1 - KOLEKSI DATA, MODE BACA SAJA
    * Firmware Uno TIDAK diubah dan TIDAK ADA satu byte pun yang dikirim
      ke Uno (tidak ada ``ser.write``).
    * Motor dikendalikan sepenuhnya oleh firmware kating; GUI hanya
      membaca, menampilkan, dan merekam.

Format baris dari Uno (115200 baud, diakhiri newline):
    *,f1,f2,f3,f4,f5,f6,f7,f8,#
contoh:
    *,0.00,-21.88,0.00,50.00,978,781,4,21.88,#
Sudut batang = kolom f2 (sudah dipastikan dengan alat asli). Kolom lain
tidak ditampilkan, tetapi baris mentah tetap disimpan utuh di CSV
(kolom ``baris_mentah``) sebagai cadangan.

Interface dibuat mirip ``SimBackend`` supaya MainWindow bisa memakai
keduanya secara bergantian.
"""

import collections
import csv
import math
import os
import re
import threading
import time

from .sim_backend import Params

try:
    import serial
    import serial.tools.list_ports
    HAVE_SERIAL = True
except ImportError:          # pyserial belum di-install
    serial = None
    HAVE_SERIAL = False

ANGLE_FIELD = 2              # f2 = sudut batang (deg), dipastikan dengan alat asli
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def list_ports():
    """Daftar (device, deskripsi) port serial. Port USB (mis. Arduino)
    diletakkan paling atas, port Bluetooth paling bawah."""
    if not HAVE_SERIAL:
        return []
    ports = list(serial.tools.list_ports.comports())
    ports.sort(key=lambda p: ("BTHENUM" in (p.hwid or ""), p.device))
    return [(p.device, f"{p.device}  \u00b7  {p.description}") for p in ports]


def parse_line(line):
    """Parse satu baris ``*,f1,...,fn,#`` dari Uno.

    Return list float (panjang n >= 1) atau None jika baris tidak valid.
    """
    line = line.strip()
    if len(line) < 3 or not line.startswith("*") or not line.endswith("#"):
        return None
    inner = line[1:-1].strip().strip(",")
    if not inner:
        return None
    try:
        return [float(x) for x in inner.split(",")]
    except ValueError:
        return None


class HardwareBackend:
    """Sumber data dari alat asli. Thread terpisah membaca serial (dan
    merekam CSV di setiap baris); GUI mengambil sampel terbaru lewat
    ``poll()``."""

    BAUD = 115200
    STALE_S = 1.0            # tanpa data selama ini -> dianggap terputus
    HISTORY_S = 0.5          # riwayat sampel untuk hitung omega
    # f2 dari Uno berlawanan tanda dengan konvensi tampilan GUI/Processing,
    # jadi secara default dibalik (dipastikan dengan alat asli).
    BASE_SIGN = -1.0
    OMEGA_WIN_S = 0.10       # jendela turunan sudut untuk omega

    def __init__(self):
        self.p = Params()
        from .sim_backend import SimBackend
        self.kp, self.ki, self.kd = SimBackend.DEFAULT_GAINS  # hanya tampilan
        self.sp = 0.0
        self.load_m, self.load_x = 0.0, 0.10           # keterangan beban fisik
        self.noise = 0.0

        # pemetaan sudut (diatur dari GUI)
        self.angle_field = ANGLE_FIELD
        self.invert = False
        self.offset = 0.0        # deg, hasil "nol-kan" (dalam satuan setelah dibalik)

        self.ser = None
        self.port = None
        self._thread = None
        self._stop = threading.Event()
        self._lock = threading.Lock()

        self._fields = None
        self._seq = 0
        self._seen_seq = 0
        self._last_rx = 0.0
        self._recent = collections.deque()     # (t_mono, fields)
        self._rx_count = 0
        self._rate_t0 = time.monotonic()
        self.rate_hz = 0.0
        self.bad_lines = 0
        self.good_lines = 0
        self.other_lines = collections.deque(maxlen=20)   # baris bukan data (teks)
        self.error = None

        # perekaman
        self._rec_lock = threading.Lock()
        self._rec_file = None
        self._rec_writer = None
        self.rec_path = None
        self.rec_label = ""
        self.rec_rows = 0
        self._rec_t0 = 0.0

        self._t0 = time.monotonic()
        self.reset()

    # ------------------------------------------------------------------
    # koneksi (BACA SAJA)
    # ------------------------------------------------------------------
    def connect(self, port):
        if not HAVE_SERIAL:
            raise RuntimeError("pyserial belum terpasang: pip install pyserial")
        self.disconnect()
        ser = serial.serial_for_url(port, do_not_open=True,
                                    baudrate=self.BAUD, timeout=0.1)
        # Coba tidak mereset Uno saat port dibuka (DTR/RTS rendah).
        # Di sebagian driver Uno tetap reset; itu normal.
        try:
            ser.dtr = False
            ser.rts = False
        except Exception:
            pass
        ser.open()
        self.ser = ser
        self.port = port
        self.error = None
        with self._lock:
            self._fields = None
            self._recent.clear()
            self._last_rx = 0.0
        self.bad_lines = self.good_lines = 0
        self.other_lines.clear()
        self._stop.clear()
        self._thread = threading.Thread(target=self._reader, daemon=True)
        self._thread.start()

    def disconnect(self):
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None
        if self.ser is not None:
            try:
                self.ser.close()
            except Exception:
                pass
            self.ser = None
        self.port = None

    @property
    def is_open(self):
        return self.ser is not None and self.ser.is_open

    @property
    def receiving(self):
        return self.is_open and (time.monotonic() - self._last_rx) < self.STALE_S

    def _reader(self):
        buf = b""
        while not self._stop.is_set():
            try:
                chunk = self.ser.read(self.ser.in_waiting or 1)
            except Exception as exc:      # kabel dicabut, Uno mati, dll.
                self.error = f"Serial terputus: {exc}"
                break
            if not chunk:
                continue
            buf += chunk
            while b"\n" in buf:
                raw, buf = buf.split(b"\n", 1)
                text = raw.decode("ascii", errors="replace").strip()
                if not text:
                    continue
                vals = parse_line(text)
                now = time.monotonic()
                if vals is None:
                    if text.startswith("*"):
                        self.bad_lines += 1        # baris data terpotong
                    else:
                        self.other_lines.append(text)   # pesan teks firmware
                    self._record(now, None, text)
                    continue
                self.good_lines += 1
                with self._lock:
                    self._fields = vals
                    self._seq += 1
                    self._last_rx = now
                    self._recent.append((now, vals))
                    while self._recent and now - self._recent[0][0] > self.HISTORY_S:
                        self._recent.popleft()
                self._rx_count += 1
                dt = now - self._rate_t0
                if dt >= 1.0:
                    self.rate_hz = self._rx_count / dt
                    self._rx_count = 0
                    self._rate_t0 = now
                self._record(now, vals, text)
            if len(buf) > 4096:           # sampah tanpa newline
                buf = b""
        self._close_recording()           # simpan file jika koneksi putus

    # ------------------------------------------------------------------
    # pemetaan sudut
    # ------------------------------------------------------------------
    def _sign(self):
        """Tanda sudut: BASE_SIGN (arah benar untuk alat ini), dibalik lagi
        jika pengguna mencentang "Balik arah"."""
        return -self.BASE_SIGN if self.invert else self.BASE_SIGN

    def _map(self, vals):
        """Sudut tampilan (deg) dari daftar kolom, atau None."""
        i = self.angle_field - 1
        if vals is None or not 0 <= i < len(vals):
            return None
        return self._sign() * vals[i] - self.offset

    def fields(self):
        with self._lock:
            return self._fields

    def raw_angle(self):
        """Sudut f2 setelah diberi tanda, TANPA offset."""
        f = self.fields()
        i = self.angle_field - 1
        if f is None or not 0 <= i < len(f):
            return None
        return self._sign() * f[i]

    def set_invert(self, invert):
        if invert != self.invert:
            self.offset = -self.offset        # titik nol fisik tetap sama
        self.invert = invert

    def tare(self):
        """Jadikan posisi sekarang sebagai 0 derajat."""
        a = self.raw_angle()
        if a is not None:
            self.offset = a

    # ------------------------------------------------------------------
    # perekaman CSV (ditulis dari thread pembaca -> setiap baris tersimpan)
    # ------------------------------------------------------------------
    @property
    def recording(self):
        return self._rec_writer is not None

    def start_recording(self, label=""):
        self.stop_recording()
        os.makedirs(DATA_DIR, exist_ok=True)
        safe = re.sub(r"[^A-Za-z0-9_-]+", "_", label.strip()).strip("_")[:40]
        name = time.strftime("hw_%Y%m%d_%H%M%S") + (f"_{safe}" if safe else "") + ".csv"
        path = os.path.join(DATA_DIR, name)
        f = open(path, "w", newline="", encoding="utf-8")
        w = csv.writer(f)
        w.writerow(["# label", label])
        w.writerow(["# port", self.port or "", "baud", self.BAUD])
        w.writerow(["# dimulai", time.strftime("%Y-%m-%d %H:%M:%S")])
        w.writerow(["t_s", "sudut_uno_f2_deg", "dibalik", "offset_deg", "sudut_deg",
                    "beban_g", "posisi_beban_cm", "baris_mentah"])
        with self._rec_lock:
            self._rec_file, self._rec_writer = f, w
            self.rec_path, self.rec_label = path, label
            self.rec_rows = 0
            self._rec_t0 = time.monotonic()
        return path

    def stop_recording(self):
        self._close_recording()

    def _close_recording(self):
        with self._rec_lock:
            if self._rec_file is not None:
                try:
                    self._rec_file.close()
                except Exception:
                    pass
            self._rec_file = self._rec_writer = None

    @property
    def rec_duration(self):
        return time.monotonic() - self._rec_t0 if self.recording else 0.0

    def _record(self, now, vals, text):
        if self._rec_writer is None:
            return
        with self._rec_lock:
            w = self._rec_writer
            if w is None:
                return
            i = self.angle_field - 1
            if vals is None or not 0 <= i < len(vals):
                raw = ang = ""                # baris teks / terpotong
            else:
                raw = f"{vals[i]:g}"
                ang = f"{self._map(vals):.3f}"
            w.writerow([f"{now - self._rec_t0:.4f}", raw, int(self.invert),
                        f"{self.offset:.3f}", ang,
                        f"{self.load_m * 1000:.0f}", f"{self.load_x * 100:.1f}", text])
            self.rec_rows += 1
            if self.rec_rows % 100 == 0:
                self._rec_file.flush()

    # ------------------------------------------------------------------
    # interface mirip SimBackend
    # ------------------------------------------------------------------
    def reset(self, keep_time=False):
        if not keep_time:
            self._t0 = time.monotonic()
        self.t = time.monotonic() - self._t0
        self.th = 0.0            # rad (kompatibel SimBackend)
        self.w = 0.0
        self.meas = self.prev_meas = 0.0
        self.u = 0.0
        self.F1 = self.F2 = 0.0
        self.I = 0.0
        self.p_term = self.i_term = self.d_term = 0.0

    def set_gains(self, kp, ki, kd):
        self.kp, self.ki, self.kd = kp, ki, kd        # tidak dikirim ke Uno

    def set_setpoint(self, deg):
        self.sp = deg                                 # tidak dikirim ke Uno

    def set_load(self, mass_kg, pos_m):
        """Keterangan beban fisik yang terpasang (untuk CSV & tampilan)."""
        self.load_m, self.load_x = mass_kg, pos_m

    def reset_integral(self):
        pass

    def apply_impulse(self, delta_w=2.0):
        pass                     # tidak berlaku di hardware

    def step(self):
        pass                     # waktu mengikuti data serial

    def _omega(self, now_deg):
        """Kecepatan sudut (deg/s) dari selisih sudut dalam OMEGA_WIN_S.
        Lebih tahan terhadap data USB yang datang bergerombol."""
        with self._lock:
            recent = list(self._recent)
        if len(recent) < 2:
            return 0.0
        t1, v1 = recent[-1]
        for t0, v0 in reversed(recent):
            if t1 - t0 >= self.OMEGA_WIN_S:
                a0 = self._map(v0)
                return 0.0 if a0 is None else (now_deg - a0) / (t1 - t0)
        return 0.0

    def poll(self):
        """Ambil sampel terbaru. Return tuple sampel (format sama dengan
        ``SimBackend.sample()``) jika ada data BARU, selain itu None."""
        with self._lock:
            vals, seq = self._fields, self._seq
        if vals is None or seq == self._seen_seq:
            return None
        self._seen_seq = seq
        deg = self._map(vals)
        if deg is None:
            return None
        self.t = time.monotonic() - self._t0
        self.th = math.radians(deg)
        self.meas = deg
        self.w = math.radians(self._omega(deg))
        return self.sample()

    def sample(self):
        deg = self.meas
        return (self.t, deg, deg, self.sp, self.u,
                self.F1, self.F2, self.p_term, self.i_term, self.d_term,
                math.degrees(self.w))
