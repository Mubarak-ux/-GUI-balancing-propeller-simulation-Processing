# Kontrol PID Hardware (Week 3)

Dokumentasi PID di alat asli (firmware `firmware/esp32_pid`). Dipisah dari
`docs/ringkasan_pengukuran.md` supaya ringkasan pengukuran tetap pendek.

| File | Isi |
|---|---|
| [`identifikasi_model.md`](identifikasi_model.md) | Model rig dari data PID nyata (k, lag motor, delay) |
| [`log_uji_pid.md`](log_uji_pid.md) | Riwayat uji PID, temuan, dan perbaikan per uji |

---

## Struktur kontrol (firmware `esp32_pid`)

```
e  = setpoint − sudut
u  = trim + Kp·e + I − Kd·(laju gyro)          (u dalam %, −100..100)
I += Ki·e·dt   hanya jika |e| < 6° dan keluaran tidak jenuh
bias = (8 + Fmax)/2,   R = (Fmax − 8)/2         (Fmax 15 → 11,5 ± 3,5 %)
kiri  = bias − u/100·R,   kanan = bias + u/100·R   (dibatasi 40 %/s per motor)
```

- Sudut + = sisi kanan naik. u > 0 → motor kanan naik.
- Loop IMU + PID 500 Hz; penulisan PWM ESC di task terpisah (core 0).
- Filter komplementer τ = 0,7 s, DLPF IMU 21 Hz (meredam getaran baling-baling).

## Pengaman

| Pengaman | Nilai |
|---|---|
| Soft-start | 0 → 8 % dalam 1 s, tahan 0,7 s, baru PID |
| Failsafe heartbeat GUI | > 0,5 s tanpa perintah → motor 0 |
| Batas mati sudut | 29–33° (slider), bisa dimatikan |
| Data IMU putus | > 50 ms → motor 0 |
| F-max | 8–15 %, terkunci + konfirmasi |

## Gain saat ini

| Kp (%/°) | Ki (%/(°·s)) | Kd (%/(°/s)) | I-zone |
|---|---|---|---|
| **2,0** | **1,5** | **1,0** | **6°** |

Cara pakai trim: setelah batang tenang di 0°, tekan **Trim ← nilai I sekarang**.
