"""Perhitungan metrik respons transien.

Konvensi (dipakai konsisten di grafik dan metrik):
    error  e = setpoint - theta
"""

import numpy as np

# Kolom data sampel: harus sinkron dengan SimBackend.sample()
COL_T, COL_TH, COL_MEAS, COL_SP, COL_U = 0, 1, 2, 3, 4
COL_F1, COL_F2, COL_P, COL_I, COL_D, COL_W = 5, 6, 7, 8, 9, 10

DASH = "\u2014"
METRIC_KEYS = ("overshoot", "rise", "peak_time", "settling", "error", "deviation")

MIN_STEP_DEG = 0.5      # step lebih kecil dari ini dianggap bukan step
LOAD_BAND_DEG = 0.5     # band settling absolut untuk gangguan beban (derajat)
SSE_MIN_S = 2.0         # steady error baru ditampilkan setelah t0 + 2 s
SSE_WINDOW_S = 1.0      # steady error = rata-rata e selama 1 s terakhir
SETTLE_SMOOTH_S = 0.2   # moving average untuk deteksi settling (redam noise)


def _moving_average(x, tt, window_s):
    """Moving average terpusat dengan lebar ``window_s`` detik."""
    if len(tt) < 3 or window_s <= 0:
        return x
    dt = float(np.median(np.diff(tt)))
    n = int(round(window_s / dt)) if dt > 0 else 1
    if n < 2:
        return x
    k = np.ones(n) / n
    pad = n // 2
    xp = np.pad(x, (pad, n - 1 - pad), mode="edge")
    return np.convolve(xp, k, mode="valid")


def _first_index(mask):
    idx = np.flatnonzero(mask)
    return int(idx[0]) if idx.size else None


def compute_metrics(d, kind, t0, crit=0.02):
    """Hitung metrik respons dari data sejak event (t >= t0).

    d     : ndarray (N x kolom sampel), baris pertama = kondisi saat event
    kind  : "sp" (step setpoint) atau "load" (gangguan beban)
    crit  : kriteria settling relatif (0.02 = 2 %, 0.05 = 5 %)

    Step setpoint: besar step diukur dari theta awal ke setpoint akhir,
    sehingga overshoot/rise time tetap benar walau theta awal belum
    tepat di setpoint lama.

    Return dict berisi string tampilan untuk METRIC_KEYS, plus
    "band" (lebar band settling, derajat) dan "sp_final".
    Return None jika data belum cukup.
    """
    if d is None or len(d) < 5:
        return None

    tt = d[:, COL_T] - t0
    th = d[:, COL_TH]
    sp = d[:, COL_SP]
    e = sp - th
    sp_f = float(sp[-1])

    res = {k: DASH for k in METRIC_KEYS}
    band = LOAD_BAND_DEG

    if kind == "sp":
        th0 = float(th[0])
        amp = sp_f - th0
        if abs(amp) >= MIN_STEP_DEG:
            y = (th - th0) / amp                  # respons ternormalisasi 0 -> 1
            ipk = int(np.argmax(y))
            os_ = max(0.0, (float(y[ipk]) - 1.0) * 100.0)
            res["overshoot"] = f"{os_:.1f} %"

            i10 = _first_index(y >= 0.1)
            i90 = _first_index(y >= 0.9)
            if i10 is not None and i90 is not None:
                res["rise"] = f"{tt[i90] - tt[i10]:.2f} s"
            else:
                res["rise"] = "not reached"

            if os_ > 0.0:
                res["peak_time"] = f"{tt[ipk]:.2f} s"
            band = crit * abs(amp)
    else:
        ipk = int(np.argmax(np.abs(e)))
        res["deviation"] = f"{abs(e[ipk]):.2f}\u00b0"
        res["peak_time"] = f"{tt[ipk]:.2f} s"

    # Deteksi settling memakai e yang dihaluskan (moving average), supaya
    # riak akibat noise sensor tidak membuat band 2 % "tidak pernah settle".
    e_s = _moving_average(e, tt, SETTLE_SMOOTH_S)
    out = np.flatnonzero(np.abs(e_s) > band)
    if out.size == 0:
        res["settling"] = "0.00 s"
    elif out[-1] >= len(tt) - 1:
        res["settling"] = "not settled"
    else:
        res["settling"] = f"{tt[out[-1] + 1]:.2f} s"

    if tt[-1] >= SSE_MIN_S:
        m = tt >= tt[-1] - SSE_WINDOW_S
        res["error"] = f"{float(np.mean(e[m])):+.2f}\u00b0"

    res["band"] = band
    res["sp_final"] = sp_f
    return res
