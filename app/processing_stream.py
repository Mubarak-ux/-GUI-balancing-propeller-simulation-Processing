"""Pengirim telemetri ke Processing 3D Viewer melalui UDP (dengan ACK)."""

import json
import socket
import time


class ProcessingStream:
    """Mengirim telemetri via UDP dan melacak status koneksi ke Processing.

    UDP tidak punya handshake, jadi "berhasil kirim" BUKAN berarti
    Processing menerima. Karena itu receiver di Processing
    membalas setiap paket dengan ``b"ack"``. Status ``healthy`` hanya
    True jika ada ACK yang masuk dalam ``HEALTHY_WINDOW`` detik terakhir.
    """

    HEALTHY_WINDOW = 1.5   # detik tanpa ACK -> dianggap terputus
    ACK = b"ack"

    def __init__(self, host="127.0.0.1", port=9999, on_impulse=None):
        self.addr = (host, port)
        self.sock = None
        self.last_ack = 0.0
        self.last_send = 0.0
        self.send_ok = False
        self._last_packet = None
        self.on_impulse = on_impulse
        self._connect()

    def _connect(self):
        if self.sock is not None:
            try:
                self.sock.close()
            except OSError:
                pass
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setblocking(False)
        try:
            self.sock.connect(self.addr)
        except OSError:
            pass

    def _poll_ack(self):
        """Kosongkan antrean balasan ACK."""
        while True:
            try:
                data = self.sock.recv(64)
            except BlockingIOError:
                return
            except OSError:
                # ICMP "port unreachable" (tidak ada listener) muncul di sini
                # sebagai ConnectionResetError; socket dibuat ulang.
                self._connect()
                return
            if data == self.ACK:
                self.last_ack = time.monotonic()
            elif data == b"impulse":
                self.last_ack = time.monotonic()
                if self.on_impulse:
                    self.on_impulse()

    def _send_raw(self, packet):
        try:
            self.sock.send(packet)
        except OSError:
            # Windows melaporkan ICMP "port unreachable" (tidak ada yang
            # listen di port tujuan) sebagai error pada send berikutnya.
            self.send_ok = False
            self._connect()
            return
        self.last_send = time.monotonic()
        self.send_ok = True

    def send(self, th, prop1, prop2, sp=0.0, u=0.0, load_m=0.0, load_x=0.0, f1=0.0, f2=0.0):
        self._poll_ack()
        packet = json.dumps({
            "th": round(th, 2),
            "prop1": round(prop1, 1),
            "prop2": round(prop2, 1),
            "sp": round(sp, 2),
            "u": round(u, 1),
            "load_m": round(load_m, 3),
            "load_x": round(load_x, 2),
            "f1": round(f1, 2),
            "f2": round(f2, 2),
        }).encode("utf-8")
        self._last_packet = packet
        self._send_raw(packet)

    def heartbeat(self):
        """Kirim ulang paket terakhir (dipakai saat simulasi di-pause),
        supaya status koneksi tetap akurat."""
        self._poll_ack()
        if self._last_packet is not None:
            self._send_raw(self._last_packet)

    @property
    def healthy(self):
        return (time.monotonic() - self.last_ack) < self.HEALTHY_WINDOW

    @property
    def sent_recently(self):
        return (self.send_ok and
                (time.monotonic() - self.last_send) < self.HEALTHY_WINDOW)

    @property
    def status(self):
        """'connected'  : ACK diterima (Processing menerima data)
        'no-ack'     : paket terkirim, tetapi Processing tidak membalas ACK
        'no-listener': tidak ada yang listen di port UDP tujuan
        'idle'       : belum pernah mengirim
        """
        if self.healthy:
            return "connected"
        if self.sent_recently:
            return "no-ack"
        return "no-listener"

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass
