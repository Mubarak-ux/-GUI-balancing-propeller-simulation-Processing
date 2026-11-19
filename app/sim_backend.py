"""Model fisika dan backend simulasi.

Model disamakan dengan ALAT ASLI (identifikasi data PID 18-11-2026,
docs/kontrol_pid/identifikasi_model.md) dan memakai hukum kontrol yang SAMA
dengan firmware esp32_pid, supaya gain yang bagus di simulasi juga bagus di
alat:

    J*th'' = L*(F2 - F1) - b*th' - k*th + c0 + asimetri + turbulensi + beban
    F_i    = F(throttle_i) dengan lag orde-1 + delay, ESC diperbarui 50 Hz
    F(u)   = 0.1241*u - 0.316 N  (timbangan, 8..15 %)

    u      = Kp*e + I - Kd*(laju gyro)          (%, -100..100)
    I     += Ki*e*dt   (penuh jika |e| < 6 deg, 50 % di luar), anti-windup
    bias   = (8 + Fmax)/2,  R = (Fmax - 8)/2
    kiri   = bias - u/100*R,  kanan = bias + u/100*R  (pembatas laju 40 %/s)
"""

import math

import numpy as np

G = 9.81


# ----------------------------------------------------------------------------
# PARAMETER ALAT (terukur / teridentifikasi)
# ----------------------------------------------------------------------------
class Params:
    """Sumber: docs/pengukuran/ringkasan_pengukuran.md & docs/kontrol_pid/."""
    L = 0.25                 # m, poros ke pusat propeler (terukur)
    J0 = 0.0140              # kg.m^2, hitungan massa + geometri
    b = 0.033                # N.m.s/rad, redaman poros (uji ayunan)
    k = -0.065               # N.m/rad, < 0: tidak stabil alami (identifikasi -0.054..-0.081)
    k_neg_extra = -0.04      # N.m/rad tambahan di sisi sudut negatif (asimetri terukur)
    c0 = 0.024               # N.m, torsi tetap (batang berat sebelah; butuh trim ~ -11 %)
    turb = 0.006             # N.m, std torsi turbulen acak (tiap 50 ms), dicocokkan ke goyangan alat
    tau = 0.15               # s, lag motor + baling-baling (identifikasi 0.10-0.15)
    delay = 0.04             # s, delay ESC + komunikasi (identifikasi 0.03-0.05)
    esc_dt = 0.02            # s, ESC membaca PWM 50 Hz
    KF, F0 = 0.1241, 0.316   # F(u) = KF*u - F0  [N], u = throttle %
    Fmin_pct = 8.0           # % throttle minimum kerja
    Fmax = 15.0              # % throttle maksimum PID (F-max), sama dengan default alat
    slew = 40.0              # %/s pembatas laju throttle (firmware)
    izone = 6.0              # deg
    iout = 0.5               # laju integral di luar I-zone
    stop = math.radians(33)  # batas mekanik sudut (terukur +/-33 deg)
    dt = 0.005               # s, periode kontrol / integrasi (200 Hz)


def thrust_n(pct):
    """Throttle (%) -> gaya dorong (N); 0 di bawah titik mulai motor."""
    return max(0.0, Params.KF * pct - Params.F0) if pct >= Params.Fmin_pct else 0.0


# ----------------------------------------------------------------------------
# BACKEND SIMULASI
# ----------------------------------------------------------------------------
class SimBackend:
    """Konvensi sudut: theta positif = sisi KANAN naik (sama dengan alat).
    F1 = motor kiri, F2 = motor kanan. u > 0 menaikkan motor kanan -> theta naik.
    Beban ada di sisi kiri -> menarik theta ke arah positif."""

    # Gain terpilih di alat asli (uji ke-7, docs/kontrol_pid/log_uji_pid.md).
    DEFAULT_GAINS = (3.0, 2.0, 1.0)   # %/deg, %/(deg.s), %/(deg/s)

    def __init__(self, seed=None):
        self.p = Params()
        self.kp, self.ki, self.kd = self.DEFAULT_GAINS
        self.sp = 0.0            # deg
        self.load_m = 0.0        # kg
        self.load_x = 0.10       # m dari poros
        self.noise = 0.15        # deg, std noise sudut (alat: ~0,15 deg diam)
        self.seed = seed
        self.reset()

    def reset(self, keep_time=False):
        """Kembalikan state dinamika & PID ke awal (batang datar, motor di bias)."""
        p = self.p
        if not keep_time:
            self.t = 0.0
        self.th = 0.0            # rad
        self.w = 0.0             # rad/s
        bias = 0.5 * (p.Fmin_pct + p.Fmax)
        self.thr_l = self.thr_r = bias        # throttle perintah (setelah slew)
        self.esc_l = self.esc_r = bias        # throttle yang sedang dibaca ESC
        self.F1 = self.F2 = thrust_n(bias)
        self._esc_t = 0.0
        self._td = 0.0                         # torsi turbulen saat ini
        self._td_t = 0.0
        nd = max(1, int(round(p.delay / p.dt)))
        self._hist = [(bias, bias)] * nd       # antrean delay perintah
        self.I = 0.0
        self.prev_meas = 0.0
        self.meas = 0.0
        self.u = 0.0
        self.p_term = self.i_term = self.d_term = 0.0
        self.rng = np.random.default_rng(self.seed)

    def set_gains(self, kp, ki, kd):
        self.kp, self.ki, self.kd = kp, ki, kd

    def set_setpoint(self, deg):
        self.sp = deg

    def set_load(self, mass_kg, pos_m):
        self.load_m, self.load_x = mass_kg, pos_m

    def reset_integral(self):
        self.I = 0.0

    def apply_impulse(self, delta_w=2.0):
        """Beri gangguan impuls pada kecepatan sudut w (rad/s)."""
        self.w += delta_w

    def step(self):
        p, dt = self.p, self.p.dt
        # --- sensor: sudut + laju gyro, bernoise ---
        self.meas = math.degrees(self.th) + self.rng.normal(0, self.noise)
        rate = math.degrees(self.w) + self.rng.normal(0, self.noise * 10.0)
        err = self.sp - self.meas
        # --- PID sama dengan firmware esp32_pid ---
        self.p_term = self.kp * err
        self.d_term = -self.kd * rate                 # D pada laju gyro
        u_raw = self.p_term + self.I + self.d_term
        u = max(-100.0, min(100.0, u_raw))
        if u == u_raw or u_raw * err < 0:             # anti-windup
            rate_i = 1.0 if abs(err) < p.izone else p.iout
            self.I += rate_i * self.ki * err * dt
        self.I = max(-100.0, min(100.0, self.I))
        self.i_term = self.I
        self.u = u
        # --- pembagian ke motor: bias tengah rentang, pembatas laju ---
        bias = 0.5 * (p.Fmin_pct + p.Fmax)
        R = 0.5 * (p.Fmax - p.Fmin_pct)
        d = u / 100.0 * R
        step = p.slew * dt
        self.thr_l += max(-step, min(step, (bias - d) - self.thr_l))
        self.thr_r += max(-step, min(step, (bias + d) - self.thr_r))
        self.thr_l = max(0.0, min(p.Fmax, self.thr_l))
        self.thr_r = max(0.0, min(p.Fmax, self.thr_r))
        # --- delay + ESC 50 Hz + lag motor ---
        self._hist.append((self.thr_l, self.thr_r))
        cmd_l, cmd_r = self._hist.pop(0)
        self._esc_t += dt
        if self._esc_t >= p.esc_dt:
            self._esc_t = 0.0
            self.esc_l, self.esc_r = cmd_l, cmd_r
        self.F1 += (thrust_n(self.esc_l) - self.F1) * dt / p.tau
        self.F2 += (thrust_n(self.esc_r) - self.F2) * dt / p.tau
        # --- dinamika batang (theta+ = kanan naik) ---
        self._td_t += dt
        if self._td_t >= 0.05:
            self._td_t = 0.0
            self._td = self.rng.normal(0, p.turb)
        m, x = self.load_m, self.load_x
        J = p.J0 + m * x * x
        k = p.k + (p.k_neg_extra if self.th < 0 else 0.0)
        tau_motor = p.L * (self.F2 - self.F1)
        tau_load = m * G * x * math.cos(self.th)       # beban kiri -> kiri turun
        acc = (tau_motor + tau_load + p.c0 + self._td - p.b * self.w - k * self.th) / J
        self.w += acc * dt
        self.th += self.w * dt
        if abs(self.th) > p.stop:
            self.th = math.copysign(p.stop, self.th)
            self.w = 0.0
        self.prev_meas = self.meas
        self.t += dt

    def sample(self):
        return (self.t, math.degrees(self.th), self.meas, self.sp, self.u,
                self.F1, self.F2, self.p_term, self.i_term, self.d_term,
                math.degrees(self.w))
