# Dokumentasi

Folder ini berisi seluruh catatan teknis & laporan proyek. README utama
(instalasi, cara menjalankan, struktur kode) ada di **[`../README.md`](../README.md)**.

## Susunan folder

```
docs/
├── README.md                 # indeks ini
├── versi2.md                 # komparasi VERSI 1 (Blender) vs VERSI 2 (Processing)
├── strukturPY.txt            # pohon direktori proyek
├── pengukuran/               # parameter fisik alat (week 1–2)
├── kontrol_pid/              # PID di alat asli (week 3)
└── assets/                   # foto tampak alat
```

## `pengukuran/` — parameter fisik alat

| Berkas | Isi |
|---|---|
| [`ringkasan_pengukuran.md`](pengukuran/ringkasan_pengukuran.md) | Massa, dimensi, momen inersia J, parameter simulasi, daftar yang belum diukur. |
| [`pengukuran_b.md`](pengukuran/pengukuran_b.md) | Redaman `b` dari uji ayunan (`b = 2·J·α`), plus cek ulang & konstanta pemulih k. |
| [`pengukuran_F.md`](pengukuran/pengukuran_F.md) | Gaya dorong F vs throttle (timbangan), batas F-min 8 % / F-max 15 %. |
| `menghitung_J.png`, `rumus_awal_momen_inersia.png` | Catatan hitungan J. |

## `kontrol_pid/` — PID hardware

| Berkas | Isi |
|---|---|
| [`README.md`](kontrol_pid/README.md) | Struktur kontrol firmware `esp32_pid`, pengaman, gain terpilih (3 / 2 / 1). |
| [`identifikasi_model.md`](kontrol_pid/identifikasi_model.md) | Model rig dari data PID nyata (k, lag motor, delay) & tuning robust. |
| [`log_uji_pid.md`](kontrol_pid/log_uji_pid.md) | Riwayat 7 uji PID 18-11-2026: hasil, temuan, perbaikan. |

## Data rekaman

CSV rekaman ada di `../data/` (tidak di-commit ke git), dikelompokkan per sesi:

| Folder | Isi |
|---|---|
| `data/2026-11-09_11_uji_awal/` | Uji baca IMU & uji ayunan (sumber `pengukuran_b.md`). |
| `data/2026-11-18_uji_pid/` | 10 rekaman uji PID (sumber `kontrol_pid/`). |

Rekaman baru dari GUI tetap tersimpan di `data/`; pindahkan ke folder sesi bila perlu.

## Parameter kunci (ringkas)

| Parameter | Nilai | Sumber |
|---|---|---|
| `L` (poros → propeller) | 0,25 m | terukur |
| `J0` (momen inersia) | 0,0140 kg·m² | hitungan massa + geometri |
| `b` (redaman poros) | 0,033 ± 0,002 N·m·s/rad | uji ayunan (motor mati) |
| `stop` (batas mekanik) | ±33° | terukur |
| `F(u)` (thrust, 8–15 %) | 0,1241·u − 0,316 N | timbangan (`pengukuran_F.md`) |
| `k` (kekakuan sudut) | −0,05 … −0,08 N·m/rad (tidak stabil alami) | identifikasi data PID |
| lag motor + delay | ~0,10–0,15 s + 0,03–0,05 s | identifikasi data PID |
| Gain PID hardware | Kp 3 / Ki 2 / Kd 1 | uji ke-7 |
