# Pengukuran Gaya Dorong `F` (Fmax / Fmin) Motor

**Status:** batas throttle ditetapkan (week 2) dan **F sudah terukur dengan timbangan** di 3 titik
(8 %, 10 %, 15 %). Titik 11 % dan seluruh rentang 8–15 % didapat dari interpolasi.

---

## 1. Batas throttle hasil uji slider (week 2)

Uji dengan slider Tes Motor di GUI (firmware `esp32_pid`, ESC sudah dikalibrasi
1000–2000 µs, PWM 50 Hz).

| Besaran | Throttle | Pulsa ESC | Duty (50 Hz) |
|---|---|---|---|
| **Fmin** | 8 % | 1080 µs | 5,40 % |
| **Fmax** | 15 % | 1150 µs | 5,75 % |

Rumus: `pulsa = 1000 + 10 × throttle%` (µs), `duty = pulsa / 20 000`.
Motor hanya boleh bergerak di rentang **8 % – 15 %**.

---

## 2. Rencana penggunaan (BUKAN week 2)

| Minggu | Isi |
|---|---|
| **Week 2 (sekarang)** | Tentukan batas Fmin/Fmax, ukur kurva thrust. **Belum ada PID.** |
| **Week 3** | Titik setimbang (bias) kedua motor = **±11 %**. PID menambah/mengurangi selisih di sekitar 11 %, keluaran dijepit ke **8 % – 15 %**. |

Titik tengah rentang = (8 + 15) / 2 = 11,5 %; dibulatkan **11 %** untuk week 3.
Motor tidak bisa menghasilkan thrust negatif, jadi bias 11 % memberi ruang naik dan turun.
Perlu anti-windup pada integral saat keluaran menyentuh 8 % atau 15 %.

---

## 3. Data pengukuran (timbangan)

Bacaan timbangan = massa ekuivalen dorongan; `F = m × g`, `g = 9,81 m/s²`.

| Throttle (%) | Pulsa (µs) | Massa terbaca (kg) | **F (N)** |
|---|---|---|---|
| 8  | 1080 | 0,070 | **0,687** |
| 10 | 1100 | 0,093 | **0,912** |
| 15 | 1150 | 0,158 | **1,550** |

Hitungan: `0,070 × 9,81 = 0,687`; `0,093 × 9,81 = 0,912`; `0,158 × 9,81 = 1,550` N.

> **Asumsi (perlu dikonfirmasi):** angka di atas adalah bacaan bersih (sudah dikurangi
> bacaan motor mati / ditare) dan merupakan satu motor. Belum dicatat: motor kiri atau
> kanan, dan tegangan power supply saat uji.

---

## 4. Kurva F(throttle) — fit

Data hampir **linear** dalam rentang 8–15 % (di sini rasio `F/u²` tidak konstan:
0,0107; 0,0091; 0,0069, jadi model kuadrat murni dari nol tidak cocok).

Kemiringan antar titik: 8→10 % = 0,113 N/% ; 10→15 % = 0,128 N/%.

Regresi linear (kuadrat terkecil, tiga titik):

```
F(u) = 0,1241 · u − 0,316        [N],  u = throttle (%),  berlaku 8 % ≤ u ≤ 15 %
```

| u (%) | F terukur (N) | F fit (N) | selisih (N) |
|---|---|---|---|
| 8  | 0,687 | 0,677 | +0,010 |
| 10 | 0,912 | 0,925 | −0,013 |
| 15 | 1,550 | 1,546 | +0,004 |

Galat fit ≤ 0,013 N (< 1,5 %). Persamaan ini **hanya untuk 8–15 %**; jangan diekstrapolasi
(mis. ke 0 % atau 100 %, karena sebenarnya ada deadband dan kurvanya melengkung).

### Nilai yang dipakai

| Parameter | Throttle | F (N) | Keterangan |
|---|---|---|---|
| **Fmin** | 8 %  | **0,69** | terukur |
| **Fbias** | 11 % | **≈ 1,05** | dari fit (interpolasi, belum diukur langsung) |
| **Fmax** | 15 % | **1,55** | terukur |

---

## 5. Dampak ke rig (pitch, pivot di tengah)

Torsi: `τ = L·(F1 − F2)`, `L = 0,25 m`, `J = 0,0140 kg·m²`.

| Kasus | ΔF (N) | τ (N·m) | α = τ/J (rad/s²) |
|---|---|---|---|
| Satu motor 15 %, lainnya 8 % (maksimum) | 0,863 | 0,216 | ≈ 15,4 |
| Dari bias 11 %: satu motor ke 15 %, lainnya ke 8 % | F1 = 1,55, F2 = 0,69 | 0,216 | ≈ 15,4 |
| Dorong-tarik simetris dari bias 11 % (batas bawah, 8 %) | ±0,36 per motor, ΔF = 0,72 | 0,180 | ≈ 12,9 |

Bias 11 % hanya punya ruang turun 3 % (≈ 0,36 N) tetapi naik 4 % (≈ 0,50 N);
untuk perintah simetris PID sebaiknya dijepit ±0,36 N ≈ ±3 % dari bias.

Catatan: `Fmax = 8,0 N` di `Params` (`sim_backend.py`) adalah tebakan untuk 100 %.
Untuk rentang kerja 8–15 % pakai tabel bagian 4. Percepatan 15 rad/s² ≈ 880°/s²
jauh lebih besar daripada gerak yang dibutuhkan; ini memberi margin untuk PID.

---

## 6. Catatan

- F1 dan F2 pasti sedikit berbeda; ukur motor kedua dengan prosedur yang sama dan
  simpan terpisah (pertimbangkan koreksi selisih di week 3).
- F bergantung pada tegangan power supply dan arus; catat dan pertahankan kondisi sama saat PID.
- Titik 11 % masih interpolasi: ukur langsung bila memungkinkan untuk mengunci bias.
- Arah dan posisi saat uji timbangan (aliran udara, ground effect dari meja) bisa menggeser F.
