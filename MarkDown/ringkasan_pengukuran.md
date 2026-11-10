# Ringkasan Pengukuran Rig Twin Rotor (Pitch 1-DOF)

Proyek: PID Twin Rotor 1-DOF Pitch, upgrade ke sistem minimum ESP32.
Tanggal data: 10 November 2026.

---

## 1. Komponen dan spesifikasi

| Komponen | Spesifikasi | Status |
|---|---|---|
| Motor | A2212, 6T, 2200 KV (2 buah) | Terukur (53 g per buah) |
| ESC | 2 buah, @30 g | Terukur |
| Propeller | 1045 (10 x 4,5 inci), 1 CW + 1 CCW | Massa diasumsikan 10 g per buah |
| Sensor | IMU, terpasang tepat di pivot | Terukur (d = 0) |
| Mikrokontroler | ESP32 (menggantikan Arduino) | - |

---

## 2. Massa

### 2.1 Massa total (tanpa PCB), 10 kali penimbangan

| Ke- | Massa (g) |
|---|---|
| 1 | 388 |
| 2 | 401 |
| 3 | 391 |
| 4 | 390 |
| 5 | 388 |
| 6 | 393 |
| 7 | 398 |
| 8 | 386 |
| 9 | 399 |
| 10 | 405 |

| Statistik | Nilai |
|---|---|
| Rata-rata | 393,9 g |
| Standar deviasi | 6,4 g |
| Galat standar rata-rata (SD/sqrt(10)) | 2,0 g |
| Rentang | 386 sampai 405 g |

**Nilai dipakai: m = 393,9 +/- 2,0 g (n = 10).**
Catatan: nilai 405 g adalah pengukuran ke-10 (terbesar), tidak dipakai sebagai massa total. Rata-rata dipilih agar tidak bias ke nilai ekstrem.

Angka ini sudah mencakup 2 motor, 2 ESC, 2 propeller, IMU, kabel, dan baut.

### 2.2 Massa tiap bagian

| Bagian | Massa (g) | Cara |
|---|---|---|
| Motor (2 x 53) | 106 | Ditimbang |
| ESC (2 x 30) | 60 | Ditimbang |
| Propeller (2 x 10) | 20 | **Asumsi** (rentang literatur 7 sampai 12 g per buah) |
| Batang + IMU + kabel + baut | 207,9 | Pengurangan: 393,9 - 106 - 60 - 20 |

---

## 3. Dimensi (diukur dari pusat poros pivot)

| Ukuran | Nilai |
|---|---|
| Panjang total batang | 54 cm (0,54 m) |
| Pivot ke pusat propeller/motor (L) | 25 cm (0,25 m) |
| Pivot ke pusat ESC 1 | 13 cm (0,130 m) |
| Pivot ke pusat ESC 2 | 13,5 cm (0,135 m) |
| Pivot ke IMU | 0 (IMU tepat di pivot) |

---

## 4. Momen inersia J (hitungan manual)

Rumus (teorema sumbu sejajar): `J = J_batang + sum(m_i * d_i^2)`, dengan `J_batang = (1/12) * m_batang * Lb^2`.

| Bagian | m (kg) | d (m) | J (kg.m^2) |
|---|---|---|---|
| Motor 1 + Motor 2 | 2 x 0,053 | 0,25 | 0,006625 |
| ESC 1 | 0,030 | 0,130 | 0,000507 |
| ESC 2 | 0,030 | 0,135 | 0,000547 |
| Propeller 1 + 2 | 2 x 0,010 | 0,25 | 0,001250 |
| IMU | - | 0 | 0 |
| Batang | 0,2079 | Lb = 0,54 | 0,005052 |
| **Total** | | | **0,01398** |

**J = 0,0140 kg.m^2** (rentang wajar 0,013 sampai 0,015).

Cek batas fisik: bila seluruh massa 0,394 kg berada di ujung batang (0,27 m), J maksimum 0,0287 kg.m^2, sehingga nilai 0,040 dari kode awal tidak mungkin benar.

Sumber galat: massa propeller (asumsi), batang dianggap seragam padahal bagian tengahnya lebih lebar, kabel dan baut dianggap menyatu dengan batang. Bandingkan juga dengan J dari model CAD.

---

## 5. Parameter simulasi terkini

```python
class Params:
    L    = 0.25                    # m, poros ke pusat propeller (terukur)
    J0   = 0.0140                  # kg.m^2, hitungan manual (m = 393,9 g)
    b    = 0.02                    # N.m.s/rad, TEBAKAN -> ukur dari peluruhan
    Fmax = 8.0                     # N, TEBAKAN batas kerja -> ukur dari tes thrust
    tau  = 0.10                    # s, lag motor + propeller (orde-1), TEBAKAN
    stop = math.radians(30)        # batas mekanik +/-30 deg (terukur)
    dt   = 0.005                   # s, 200 Hz
```

---

## 6. Belum diukur (to-do)

| Parameter | Cara ukur | Prioritas |
|---|---|---|
| Kurva thrust F(PWM), motor kiri dan kanan terpisah | Motor di atas timbangan, naikkan PWM bertahap, catat selisih gram x 0,00981 = N | Tinggi |
| Deadband PWM | Titik PWM saat bacaan timbangan mulai berubah | Tinggi |
| Tegangan dan rating arus power supply | Baca label | Tinggi |
| Rating arus ESC | Baca label ESC | Tinggi |
| Redaman b | Beri dorongan awal tanpa motor, catat peluruhan kecepatan sudut dari IMU | Sedang |
| Batas sudut mekanik (stop) | Ukur sudut maks sebelum batang menabrak | Sedang |
| Titik setimbang (pusat massa l) | Cek apakah batang diam di sudut sembarang tanpa motor | Sedang |
| Offset IMU | Cek horizontal dengan waterpass, baca IMU | Sedang |
| Noise IMU | Diamkan batang, hitung SD pembacaan sudut | Sedang |
| Konstanta waktu motor tau | Respons thrust terhadap step PWM | Rendah |
| Massa propeller sebenarnya | Timbang 1 buah | Rendah |

---

## 7. Catatan penting

- Motor 2200 KV dengan propeller 10 inci beban arusnya tinggi. Naikkan PWM pelan-pelan saat tes thrust, tahan tiap titik 3 sampai 5 detik, dan pantau suhu motor dan ESC.
- Motor tidak bisa menghasilkan thrust negatif, jadi perlu **thrust dasar (bias)** pada kedua motor, lalu PID menambah dan mengurangi selisihnya. Batasi `0 <= F <= Fmax` di simulasi dan tangani integral windup.
- Jika `l` sekitar 0 (pusat massa di pivot), suku gravitasi dibuang: `J*theta'' = L*(F1 - F2) - b*theta'`. Asumsi ini **belum diverifikasi**.
- Cek refresh rate ESC. Banyak ESC standar memakai PWM 50 Hz, sehingga loop 200 Hz belum tentu berarti 200 perintah baru per detik sampai ke motor.
