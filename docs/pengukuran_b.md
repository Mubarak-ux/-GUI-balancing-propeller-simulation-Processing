# Pengukuran Koefisien Redaman `b`

**Metode:** uji ayunan bebas (motor mati, tanpa beban), fit
`θ(t) = off + A·e^(−αt)·cos(ω_d·t + φ)`.
**Data:** `hw_20261111_211524` (14,15 s, ~136 Hz, dua gangguan).

---

## 1. Rumus

Dari `J·θ̈ + b·θ̇ + k·θ = 0` → `b = 2·J·α`

| Simbol | Arti | Nilai |
|---|---|---|
| `J` | Momen inersia | 0,0140 kg·m² |
| `α` | Laju peluruhan amplitudo (hasil fit) | 1,13 – 1,34 /s |
| `b` | Koefisien redaman | → dicari |

Dengan `2·J0 = 0,0280`, maka **`b = 0,0280 × α`**.

> **α dari mana?** Fit kurva `A·e^(−αt)` ke data sudut saat ayunan bebas.
> Manual: `α = ln(A₁/A₂) / Δt` (dua puncak searah).

---

## 2. Hasil

| Event | α (1/s) | R² | b = 0,0280·α |
|---|---|---|---|
| Dorongan 1 (−4,8°) | 1,3378 ± 0,0342 | 0,922 | 0,0375 |
| Dorongan 2 (+14,4°) | 1,1335 ± 0,0160 | 0,969 | 0,0317 |
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

## 4. Langkah lanjut (opsional)

Ukur `J` langsung lewat **bandul bifilar** `J = T²·m·g·d² / (4π²·L)`,
lalu hitung ulang `b = 2·J_ukur·α` dengan `α` yang sama.
