"""Model fisika dan backend simulasi."""

import math

import numpy as np

G = 9.81


# ----------------------------------------------------------------------------
# PARAMETER ALAT
# ----------------------------------------------------------------------------
class Params:
    """Sumber: docs/ringkasan_pengukuran.md (10 Nov 2026)."""
    L = 0.25                 # m, poros ke pusat propeler (terukur)
    J0 = 0.0140              # kg.m^2, hitungan manual (m = 393,9 g)
    b = 0.033                # N.m.s/rad, redaman poros (ukur: docs/pengukuran_b.md)
    Fmax = 8.0               # N, thrust maks per motor (tebakan)
    tau = 0.10               # s, lag motor + propeler (orde-1, tebakan)
    stop = math.radians(30)  # batas mekanik sudut (terukur +/-30 deg)
    dt = 0.005               # s, periode kontrol / integrasi (200 Hz)
# ----------------------------------------------------------------------------
# BACKEND SIMULASI
# ----------------------------------------------------------------------------
class SimBackend:
    """Konvensi sudut: theta positif = sisi KANAN naik (sama dengan tampilan
    2D/3D dan dengan sudut alat asli di mode hardware).
    F1 = motor kiri, F2 = motor kanan. u > 0 menambah F2 -> theta naik.
    Beban ada di sisi kiri -> menarik theta ke arah positif."""

    # Gain default hasil tuning pada model terukur (L, J0, Fmax, tau di atas),
    # diuji dengan 5 skenario GUI + noise 0.2 deg:
    #   step +-10 deg : overshoot ~17 %, settling ~4 s
    #   beban 400 g @ 15 cm : deviasi ~25 deg, tidak menabrak batas +-30 deg
    # Batas stabil (tanpa filter D): Kp < 0.2 + 11.4*Kd.
    DEFAULT_GAINS = (1.00, 0.80, 0.35)   # %/deg, %/(deg.s), %/(deg/s)

    def __init__(self, seed=None):
        self.p = Params()
        self.kp, self.ki, self.kd = self.DEFAULT_GAINS
        self.sp = 0.0            # deg
        self.load_m = 0.0        # kg
        self.load_x = 0.10       # m dari poros (10 cm default, rentang 5 - 15 cm)
        self.noise = 0.2         # deg, std noise IMU
        # seed tetap -> noise reproducible (berguna untuk laporan & skenario
        # otomatis); None -> berbeda tiap run.
        self.seed = seed
        self.reset()

    def reset(self, keep_time=False):
        """Kembalikan state dinamika & PID ke awal.

        keep_time=True dipakai skenario otomatis: state di-reset supaya
        tiap skenario mulai dari kondisi yang sama, tapi sumbu waktu grafik
        tetap kontinu.
        """
        F0 = self.p.Fmax / 2
        if not keep_time:
            self.t = 0.0
        self.th = 0.0            # rad
        self.w = 0.0             # rad/s
        self.F1 = self.F2 = F0   # thrust kiri / kanan
        self.I = 0.0
        self.d_f = 0.0
        self.prev_meas = 0.0
        self.meas = 0.0
        self.u = 0.0
        self.p_term = 0.0
        self.i_term = 0.0
        self.d_term = 0.0
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
        # --- sensor IMU (sudut + noise) ---
        self.meas = math.degrees(self.th) + self.rng.normal(0, self.noise)
        err = self.sp - self.meas
        # --- PID: D pada pengukuran + filter 20 ms ---
        alpha = dt / (0.02 + dt)
        self.d_f += alpha * ((self.meas - self.prev_meas) / dt - self.d_f)
        self.prev_meas = self.meas
        self.p_term = self.kp * err
        self.d_term = -self.kd * self.d_f
        u_raw = self.p_term + self.I + self.d_term
        u = max(-100.0, min(100.0, u_raw))
        # anti-windup
        if u == u_raw or u_raw * err < 0:
            self.I += self.ki * err * dt
        self.I = max(-100.0, min(100.0, self.I))
        self.i_term = self.I
        self.u = u
        # --- motor: u (%) -> thrust diferensial di sekitar bias Fmax/2 ---
        # |u| <= 100 menjamin 0 <= F <= Fmax (motor tidak bisa thrust negatif)
        c1 = p.Fmax * (0.5 - u / 200.0)      # kiri
        c2 = p.Fmax * (0.5 + u / 200.0)      # kanan
        self.F1 += (c1 - self.F1) * dt / p.tau
        self.F2 += (c2 - self.F2) * dt / p.tau
        # --- dinamika batang (theta+ = kanan naik) ---
        # Pusat massa batang dianggap di poros (l = 0, belum diverifikasi),
        # jadi gravitasi hanya dari beban tambahan.
        m, x = self.load_m, self.load_x
        J = p.J0 + m * x * x
        tau_motor = p.L * (self.F2 - self.F1)
        tau_load = m * G * x * math.cos(self.th)   # beban kiri -> kiri turun
        acc = (tau_motor + tau_load - p.b * self.w) / J
        self.w += acc * dt
        self.th += self.w * dt
        if abs(self.th) > p.stop:
            self.th = math.copysign(p.stop, self.th)
            self.w = 0.0
        self.t += dt

    def sample(self):
        return (self.t, math.degrees(self.th), self.meas, self.sp, self.u,
                self.F1, self.F2, self.p_term, self.i_term, self.d_term,
                math.degrees(self.w))
