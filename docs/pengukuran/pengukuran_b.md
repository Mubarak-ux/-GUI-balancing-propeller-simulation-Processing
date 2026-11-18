# Pengukuran Koefisien Redaman `b`

**Metode:** uji ayunan bebas (motor mati, tanpa beban), fit
`θ(t) = off + A·e^(−αt)·cos(ω_d·t + φ)`.
**Data:** `data/2026-11-09_11_uji_awal/hw_20261111_211524` (14,15 s, ~136 Hz, dua gangguan).

---

## 1. Rumus

Dari `J·θ̈ + b·θ̇ + k·θ = 0` → `b = 2·J·α`

dengan `J = 0,0140 kg·m²`, sehingga **`b = 0,0280 × α`**.

> Manual (dua puncak searah): `b = 2·J·ln(A₁/A₂) / Δt`

---

## 2. Hasil

| Event | α (1/s) | R² | b |
|---|---|---|---|
| Dorongan 1 (−4,8°) | 1,3378 | 0,922 | 0,0375 |
| Dorongan 2 (+14,4°) | 1,1335 | 0,969 | 0,0317 |
| **Berbobot (1/σ²)** | — | — | **0,0328 ± 0,0004** |

### **`b ≈ 0,033 ± 0,002 N·m·s/rad`** (rentang wajar 0,031 – 0,038)

---

## 3. Poin kunci

- **`J` dan `b` tak bisa dipisah** dari satu uji ayunan — hanya `b/J = 2α` yang terukur.
  Jadi `b` proporsional terhadap `J` (pakai `J` hasil hitungan, bukan ukur langsung).
- **Jangan** pakai `b` ini untuk mencari `J` → hasilnya melingkar.
- `b` hanya mencakup **gesekan poros**; redaman aerodinamis saat baling-baling berputar belum termasuk.
- Tebakan lama 0,02 terlalu kecil (~1,7×).
- `DEFAULT_GAINS` dituning dengan `b = 0,02` → **perlu tuning ulang PID**.

---

## 3a. Cek ulang (2026-11-18)

Data `hw_20261111_211524` difit ulang dengan model yang sama, J = 0,0140 kg·m².

| Event | α (1/s) | ω_d (rad/s) | R² | b = 2·J·α |
|---|---|---|---|---|
| Dorongan 2 (+14,4°), jendela 5 s | 1,158 | 1,187 | 0,970 | **0,0324** |
| Dorongan 1 (−4,8°), jendela 5 s | 1,612 | 1,397 | 0,929 | 0,0451 |

- **Rumus `b = 2·J·α` benar** untuk sistem teredam kurang (`θ̈ + (b/J)θ̇ + (k/J)θ = 0`, α = laju peluruhan amplop).
- Dorongan 2 (amplitudo besar, R² 0,970) cocok dengan angka lama (α 1,13 → b 0,032).
- Dorongan 1 (amplitudo kecil, −4,8°) **sensitif ke jendela fit**: α berkisar 1,34–1,61, sehingga b 0,037–0,045. Maka rentang wajar b sebaiknya dilonggarkan: **0,032 – 0,045**; nilai pakai tetap **b ≈ 0,033** (berpatokan pada event 2).
- **Parameter baru dari F tidak mengubah `b`:** `b` berasal dari uji ayunan (motor mati), tidak bergantung pada F atau throttle 8–15 %. J = 0,0140 juga tidak berubah.

**Konstanta pemulih (hasil sampingan).** Dari event 2: `ω_n² = ω_d² + α² = 2,75`, jadi
`k = J·ω_n² ≈ 0,039 N·m/rad`, damping ratio `ζ = α/ω_n ≈ 0,70`.
Bila k berasal dari pusat massa di bawah pivot: `l = k/(m·g) = 0,039/(0,393·9,81) ≈ 10 mm`.
Torsi pemulih pada sudut 33° (batas mekanik) ≈ 0,022 N·m, sekitar **10 %** dari torsi maksimum motor
(0,216 N·m, lihat `pengukuran_F.md`). Kecil tapi tidak nol; asumsi `l = 0` di simulasi
sedikit mengabaikannya.

---

## 4. Langkah lanjut (opsional)

Ukur `J` langsung lewat **bandul bifilar** `J = T²·m·g·d² / (4π²·L)`,
lalu hitung ulang `b = 2·J_ukur·α` dengan `α` yang sama.