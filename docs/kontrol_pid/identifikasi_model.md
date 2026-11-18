# Identifikasi Model Rig dari Data PID

**Metode:** simulasi loop tertutup (PID firmware yang sama, setpoint & trim dari
CSV) dicocokkan ke sudut terukur dengan Nelder-Mead.
**Data:** `hw_20261118_175628_-10.csv` (Kp 1,5 / Ki 0,6 / Kd 1,0) dan
`hw_20261118_180513_-_10kedua.csv` (Kp 2,5 / Ki 2,0 / Kd 1,0).

## Model

```
J·θ̈ = L·g_F·(F2 − F1) − b·θ̇ − k·θ + c0
F_i  : orde-1 (lag τ) + delay, dari throttle lewat F(u) = 0,1241·u − 0,316 N
```

J = 0,0140 kg·m², b = 0,033 N·m·s/rad, L = 0,25 m (dari pengukuran sebelumnya).

## Hasil

| Parameter | Fit data Kp 1,5 | Fit gabungan 2 data | Satuan |
|---|---|---|---|
| **k** | −0,081 | −0,054 | N·m/rad |
| τ (lag motor + baling) | 0,15 | 0,10 | s |
| delay | 0,05 | 0,03 | s |
| g_F (skala thrust) | 1,09 | 0,74 | – |
| RMS error sudut | 2,3 | 2,5 | ° |

Validasi: dengan gain 1,5/0,6/1,0 model memberi overshoot ~60 % dan settling
~7,5 s untuk step 10°, sama dengan data.

## Interpretasi

- **k negatif → batang tidak stabil alami** (seperti pendulum terbalik): makin
  miring, makin kuat jatuh ke sisi itu. Cocok dengan batang yang selalu diam di
  batas mekanik (±31–33°) saat motor mati.
- Uji ayunan 11-11 (`docs/pengukuran_b.md`) memberi k = +0,039 (stabil). Kemungkinan
  susunan rig berubah sejak itu (ESP32/kabel di atas poros menaikkan pusat massa).
  Perlu dicek ulang.
- Parameter berbeda antar data (k −0,05..−0,08, g_F 0,7..1,1) → tuning dibuat
  **robust**: gain diuji pada beberapa varian model (τ ×1,6, delay +40 ms) plus
  noise sensor dan torsi turbulen acak.

## Tuning robust (simulasi, step 0 → +10 → −10°)

| Kp/Ki/Kd, I-zone | Error tunak maks | Std sudut | Overshoot maks |
|---|---|---|---|
| 2,5 / 2,0 / 1,0, 3° (uji ke-4) | 3,9° | 0,89° | 7,2° |
| **2,0 / 1,5 / 1,0, 6°** | **0,2°** | **0,48°** | **4,8°** |
| 2,0 / 0,8 / 1,0, tanpa I-zone | 0,2° | 0,46° | 6,9° |

- I-zone 3° menahan error tunak sampai ~4° (integral tidak jalan jika |e| > 3°).
- Kp 2,5 menambah osilasi; Kp 2,0 paling tenang di semua varian model.
- Osilasi kecil (~0,5°) tetap ada di model karena turbulensi/variasi thrust; tidak
  realistis mengharapkan sudut benar-benar diam.

## Cara paling efektif mengurangi osilasi (fisik)

Turunkan/seimbangkan pusat massa batang (pindahkan PCB/kabel ke bawah atau dekat
poros) agar k mendekati 0 atau positif, dan seimbangkan baling-baling.
