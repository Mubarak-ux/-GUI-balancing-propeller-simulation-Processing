"""Pengirim telemetri ke Processing dengan data tambahan mode hardware.

Turunan dari ``ProcessingStream`` (file aslinya tidak diubah). Paket JSON
tetap berisi kunci lama (th, prop1, prop2, sp, u, load_m, load_x, f1, f2)
sehingga ``BalancingPropellerIMU`` tetap bisa membaca, ditambah
kunci dari ``extra``:

    mode  : "sim" / "hw"
    conn  : 1 jika data Uno sedang masuk
    port  : nama port (mis. "COM19")
    inv   : 1 jika arah dibalik
    off   : offset nol (deg)
    rate  : laju data Uno (Hz)
    rec   : 1 jika sedang merekam
    lbl   : label rekaman
"""

import json

from .processing_stream import ProcessingStream


class TelemetryStream(ProcessingStream):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.extra = {}

    def send(self, th, prop1, prop2, sp=0.0, u=0.0, load_m=0.0, load_x=0.0, f1=0.0, f2=0.0):
        self._poll_ack()
        data = {
            "th": round(th, 2),
            "prop1": round(prop1, 1),
            "prop2": round(prop2, 1),
            "sp": round(sp, 2),
            "u": round(u, 1),
            "load_m": round(load_m, 3),
            "load_x": round(load_x, 2),
            "f1": round(f1, 2),
            "f2": round(f2, 2),
        }
        data.update(self.extra)
        packet = json.dumps(data).encode("utf-8")
        self._last_packet = packet
        self._send_raw(packet)
