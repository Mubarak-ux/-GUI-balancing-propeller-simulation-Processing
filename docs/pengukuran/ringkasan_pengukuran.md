# Ringkasan Pengukuran Rig Twin Rotor (Pitch 1-DOF)

Proyek: PID Twin Rotor 1-DOF Pitch, upgrade dari Arduino Uno ke ESP32.
Periode data: 9–18 November 2026.
Status: **semua nilai di bawah adalah hasil terbaru yang valid**. Nilai yang
masih asumsi atau belum diukur ditandai jelas.

---

## 0. Ringkasan cepat

| Parameter | Nilai | Cara |
|---|---|---|
| Massa total rig | 393,9 ± 2,0 g | 10× timbang |
| Panjang batang | 0,54 m | ukur |
| Lengan motor `L` (poros → motor) | 0,25 m | ukur |
| Momen inersia `J` | 0,0140 kg·m² (0,013–0,015) | hitung dari massa + geometri |
| Batas sudut mekanik | ±33° | ukur |
| Redaman poros `b` | 0,033 N·m·s/rad (0,032–0,045) | uji ayunan, motor mati |
| Rentang throttle kerja | 8 % (F-min) – 15 % (F-max) | uji slider |
| Gaya dorong `F(u)` (8–15 %) | `0,1241·u − 0,316` N | timbangan |
| F pada 8 / 11 / 15 % | 0,69 / ≈1,05 / 1,55 N | timbangan (11 % interpolasi) |
| Kekakuan sudut `k` (motor menyala) | −0,054 … −0,081 N·m/rad (**tidak stabil**) | identifikasi data PID |
| Lag motor + baling-baling `τ` | 0,10–0,15 s | identifikasi data PID |
| Delay (ESC + komunikasi) | 0,03–0,05 s | identifikasi data PID |
| Gain PID terpilih | Kp 3 / Ki 2 / Kd 1 | uji di alat |

---

## 1. Komponen dan wiring

| Komponen | Spesifikasi | Catatan |
|---|---|---|
| Motor | 2× A2212 6T 2200 KV, brushless | 53 g/buah (timbang) |
| ESC | 2× Readytosky 30 A | 30 g/buah (timbang). Dikalibrasi 1000–2000 µs |
| Propeller | 1045 (10 × 4,5 inci), 1 CW + 1 CCW | massa diasumsikan 10 g/buah |
| Sensor | IMU GY-521 (MPU6050), tepat di poros | d = 0 |
| Mikrokontroler | ESP32 DevKit V1 | menggantikan Arduino Uno |
| Daya motor | power supply ~11–12 V (setara LiPo 3S) | ESC mendeteksi 3S (3 beep) |

| Sinyal | Pin ESP32 |
|---|---|
| ESC motor kiri (CCW) | GPIO 26 |
| ESC motor kanan (CW) | GPIO 25 |
| IMU SDA / SCL | GPIO 21 / GPIO 22 (I2C 400 kHz) |
| LED status | GPIO 2 |

GND sinyal ESC wajib disambung ke GND ESP32. Kabel merah 5 V (BEC) ESC tidak
disambung ke ESP32.

Konvensi: **sudut + = sisi kanan naik**. Motor kiri = F1, motor kanan = F2.

---

## 2. Massa

### 2.1 Massa total, 10 kali penimbangan

| Ke- | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| Massa (g) | 388 | 401 | 391 | 390 | 388 | 393 | 398 | 386 | 399 | 405 |

| Statistik | Nilai |
|---|---|
| Rata-rata | 393,9 g |
| Standar deviasi | 6,4 g |
| Galat standar rata-rata (SD/√10) | 2,0 g |
| Rentang | 386–405 g |

**Nilai dipakai: m = 393,9 ± 2,0 g.** Penimbangan ulang 11-11-2026: 393,3 g
(konsisten). Sudah mencakup 2 motor, 2 ESC, 2 propeller, IMU, kabel, baut;
**belum termasuk PCB ESP32** yang dipasang belakangan.

### 2.2 Massa tiap bagian

| Bagian | Massa (g) | Cara |
|---|---|---|
| Motor (2 × 53) | 106 | timbang |
| ESC (2 × 30) | 60 | timbang |
| Propeller (2 × 10) | 20 | **asumsi** (literatur 7–12 g/buah) |
| Batang + IMU + kabel + baut | 207,9 | sisa: 393,9 − 106 − 60 − 20 |

---

## 3. Dimensi (dari pusat poros)

| Ukuran | Nilai |
|---|---|
| Panjang total batang | 0,54 m |
| Poros → pusat motor/propeller (`L`) | 0,25 m |
| Poros → ESC 1 / ESC 2 | 0,130 m / 0,135 m |
| Poros → IMU | 0 |
| Batas sudut mekanik | **±33°** |

---

## 4. Momen inersia J

```
J = J_batang + Σ m_i·d_i²,      J_batang = (1/12)·m_batang·Lb²   (poros di tengah)
```

| Bagian | m (kg) | d (m) | J (kg·m²) |
|---|---|---|---|
| Motor 1 + 2 | 2 × 0,053 | 0,25 | 0,006625 |
| ESC 1 | 0,030 | 0,130 | 0,000507 |
| ESC 2 | 0,030 | 0,135 | 0,000547 |
| Propeller 1 + 2 | 2 × 0,010 | 0,25 | 0,001250 |
| Batang | 0,2079 | Lb = 0,54 | 0,005052 |
| **Total** | | | **0,01398** |

**J = 0,0140 kg·m²** (wajar 0,013–0,015). Batas fisik: semua massa di ujung
batang → J maks 0,0287, jadi nilai lama 0,040 di kode awal tidak mungkin.

Sumber galat: massa propeller (asumsi), batang dianggap seragam, kabel/baut
dianggap menyatu dengan batang, PCB ESP32 belum dihitung.

---

## 5. Redaman poros b (uji ayunan, motor mati)

Model: `J·θ̈ + b·θ̇ + k·θ = 0` → `b = 2·J·α` (α = laju peluruhan amplop).
Fit `θ(t) = off + A·e^(−αt)·cos(ω_d·t + φ)` pada data
`hw_20261111_211524` (14 s, ~136 Hz, dua dorongan).

| Event | α (1/s) | ω_d (rad/s) | R² | b (N·m·s/rad) |
|---|---|---|---|---|
| Dorongan 2 (+14,4°) | 1,13–1,16 | 1,19 | 0,97 | **0,032** |
| Dorongan 1 (−4,8°) | 1,34–1,61 (sensitif jendela fit) | 1,40 | 0,92–0,93 | 0,037–0,045 |

**b ≈ 0,033 N·m·s/rad** (rentang wajar 0,032–0,045). Hanya gesekan poros;
redaman aerodinamis baling-baling belum termasuk. b sebanding dengan J, jadi
ketidakpastian J ikut masuk ke b.

Hasil sampingan saat itu (motor mati): `k = J·(ω_d² + α²) ≈ +0,039 N·m/rad`,
ζ ≈ 0,70 → berarti pada 11-11 batang **stabil** (pusat massa ~10 mm di bawah
poros). Lihat bagian 7: dengan motor menyala dan ESP32 terpasang, k terukur
**negatif**.

---

## 6. Gaya dorong F

### 6.1 Sinyal ESC

| Besaran | Nilai |
|---|---|
| PWM | 50 Hz, pulsa 1000 µs (0 %) – 2000 µs (100 %) |
| Rumus | `pulsa = 1000 + 10 × throttle%` µs, `duty = pulsa / 20 000` |
| Kalibrasi ESC | 2000 µs saat ESC dinyalakan → beep → 1000 µs → beep |

### 6.2 Batas throttle kerja (uji slider)

| Besaran | Throttle | Pulsa |
|---|---|---|
| **F-min** | 8 % | 1080 µs |
| **F-max** | 15 % | 1150 µs |

### 6.3 Gaya dorong (timbangan, satu motor)

| Throttle | Pulsa | Massa terbaca | **F** |
|---|---|---|---|
| 8 % | 1080 µs | 0,070 kg | **0,687 N** |
| 10 % | 1100 µs | 0,093 kg | **0,912 N** |
| 15 % | 1150 µs | 0,158 kg | **1,550 N** |

Fit linear (galat ≤ 0,013 N, < 1,5 %), **berlaku hanya 8–15 %**:

```
F(u) = 0,1241·u − 0,316   [N],   u = throttle (%)
```

F pada 11 % ≈ 1,05 N (interpolasi).

### 6.4 Bias dan daya koreksi PID

```
bias = (8 + Fmax)/2,   rentang koreksi R = (Fmax − 8)/2
kiri = bias − u/100·R,   kanan = bias + u/100·R
```

| F-max | Bias | Koreksi | Torsi maks `L·ΔF` |
|---|---|---|---|
| 15 % | 11,5 % | ±3,5 % | ≈ 0,217 N·m |
| 10 % | 9,0 % | ±1,0 % | ≈ 0,062 N·m (terlalu lemah) |

Selisih maksimum 15 % vs 8 %: ΔF = 0,86 N → τ = 0,216 N·m → α = τ/J ≈ 15 rad/s².

---

## 7. Identifikasi dinamik dari data PID (motor menyala)

Model: `J·θ̈ = L·g_F·(F2 − F1) − b·θ̇ − k·θ + c0`, F orde-1 (lag τ) + delay.
Dicocokkan dengan simulasi loop tertutup ke rekaman uji PID 18-11-2026.

| Parameter | Fit data 1 | Fit 2 data | Satuan |
|---|---|---|---|
| **k** | −0,081 | −0,054 | N·m/rad |
| τ (lag motor + baling-baling) | 0,15 | 0,10 | s |
| delay | 0,05 | 0,03 | s |
| g_F (skala thrust) | 1,09 | 0,74 | – |
| RMS galat sudut | 2,3 | 2,5 | ° |

Temuan penting:
- **k negatif → batang tidak stabil alami** (seperti pendulum terbalik): tanpa
  kontrol batang selalu jatuh ke batas mekanik (diam di ±31–33°). Berbeda dengan
  uji ayunan 11-11 (k positif) → kemungkinan pusat massa naik setelah ESP32/kabel
  dipasang. Perlu dicek ulang.
- **Tidak simetris**: sisi negatif jatuh lebih kuat. Untuk diam di −22° butuh
  u ≈ +10 %, di 0° butuh u ≈ −11 %.
- **Torsi tetap** (batang berat sebelah / thrust kiri-kanan beda): butuh trim
  u ≈ −10 … −13 % agar diam di 0° (motor kiri ~1 % throttle lebih tinggi).
- **Getaran**: accelerometer bergetar 0,21 g saat motor menyala (0,002 g saat
  mati) → filter sudut perlu konstanta waktu panjang (τ = 0,7 s, DLPF 21 Hz).

---

## 8. Hasil kontrol PID terpilih (Kp 3 / Ki 2 / Kd 1)

Firmware `esp32_pid`: loop 500 Hz, soft-start, pembatas laju 40 %/s,
I-zone 6° (integral 50 % di luar zona), F-max 15 %.
Data: `hw_20261118_184438_-_10PID3_2_1`.

| Setpoint | Rata-rata akhir | Std | Lewat setpoint | Waktu tenang (±1,5°) |
|---|---|---|---|---|
| 0° | +0,3° | 0,55° | 1,3° | – |
| +10° | +9,6° | 0,40° | 4,9° | 2,3 s |
| −10° | −10,2° | 0,76° | 9,3° | ~3 s |
| +20° | +20,2° | 0,51° | 10,8° | 3,7 s |
| −20° (step 40°) | −19,8° | 1,3° | sampai batas mekanik | ~5 s |

Perbandingan gain lama 2 / 1,5 / 1: std di 0° turun dari ~2° ke 0,55°, waktu
tenang ±10° turun dari ~9 s ke 2–3 s.

---

## 9. Parameter model untuk simulasi

```python
L    = 0.25          # m, terukur
J0   = 0.0140        # kg.m^2, hitungan (0,013–0,015)
b    = 0.033         # N.m.s/rad, uji ayunan (motor mati)
k    = -0.054..-0.081  # N.m/rad, identifikasi (motor menyala) -> tidak stabil
F(u) = 0.1241*u - 0.316  # N, u = 8..15 %
tau  = 0.10..0.15    # s, lag motor + baling-baling
delay= 0.03..0.05    # s
stop = 33 deg        # batas mekanik
```

Catatan: `app/sim_backend.py` masih memakai nilai lama (`Fmax = 8 N` tebakan,
`tau = 0,10 s`, `l = 0`); belum diperbarui ke nilai di atas.

---

## 10. Belum diukur / ketidakpastian

| Parameter | Status | Cara ukur |
|---|---|---|
| Kurva F motor kedua | Baru 1 motor diukur | timbangan, prosedur sama |
| Tegangan & arus power supply saat uji | Belum dicatat | baca label / multimeter |
| J absolut independen | Masih hitungan | bandul bifilar `J = T²·m·g·d²/(4π²·L)` |
| Massa propeller | Asumsi 10 g | timbang 1 buah |
| Massa & posisi PCB ESP32 | Belum masuk J | timbang + ukur jarak |
| Penyebab k negatif & asimetri | Dugaan: pusat massa naik / kabel | uji lepas motor mati setelah rig dirapikan |
| Redaman aerodinamis saat motor menyala | Belum dipisah dari b | uji ayunan dengan motor di bias |

---

## 11. Catatan penting

- Motor 2200 KV dengan baling-baling 10 inci menarik arus besar: naikkan throttle
  pelan, pantau suhu motor & ESC.
- Motor tidak bisa thrust negatif → PID bekerja di sekitar **bias** kedua motor.
- ESC hanya membaca PWM 50 Hz; loop kontrol 500 Hz tidak berarti 500 perintah/s
  sampai ke motor.
- Start motor dari 0 langsung ke throttle tinggi bisa membuat ESC desync →
  firmware memakai soft-start (0 → 8 % dalam 1 s).
- Perbaikan paling efektif berikutnya bersifat **fisik**: seimbangkan dan turunkan
  pusat massa batang agar k mendekati nol atau positif.
