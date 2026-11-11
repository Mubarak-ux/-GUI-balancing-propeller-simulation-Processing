# Pengukuran Koefisien Redaman b

Tanggal: 2026-11-11
Metode: uji ayunan bebas (batang diberi gangguan, motor mati, tanpa beban),
fit osilasi teredam `off + A·e^(−αt)·cos(ω_d·t + φ)`.

Ringkas: yang terukur langsung dari gerak hanyalah **α** (laju peluruhan).
Redaman dihitung dengan **`b = 2·J·α`**, memakai `J = 0,0140 kg·m²`
(hitungan dari massa + geometri, `docs/ringkasan_pengukuran.md`).

## Penurunan rumus b

Model ayunan teredam dengan torsi pemulih `k·θ`:

```
J·θ̈ + b·θ̇ + k·θ = 0
```

Bagi dengan J lalu samakan dengan bentuk standar osilasi teredam
`θ̈ + 2·ζ·ωₙ·θ̇ + ωₙ²·θ = 0`:

```
2·ζ·ωₙ = b / J
```

Solusi persamaan tersebut adalah
`θ(t) = off + A·e^(−αt)·cos(ω_d·t + φ)` dengan laju peluruhan
`α = ζ·ωₙ`. Substitusi ke persamaan di atas:

```
b = 2 · J · α
```

dengan:
- `J` = `J0` = 0,0140 kg·m² (momen inersia, `docs/ringkasan_pengukuran.md`)
- `α` = laju peluruhan eksponensial hasil fit (satuan 1/s)

Satuan: `kg·m² × 1/s = kg·m²/s = N·m·s/rad`.

Faktor tetap: `2·J0 = 2 × 0,0140 = 0,0280`, sehingga `b = 0,0280 × α`.

### Versi manual (tanpa software)
Kalau hanya ingin menghitung dengan kalkulator dari grafik, pakai dua puncak
berurutan yang **searah** (amplitudo A₁ dan A₂, selang waktu Δt):

```
δ = ln(A₁ / A₂)        (logarithmic decrement)
α = δ / Δt
b = 2 · J · α = 2 · J · ln(A₁/A₂) / Δt
```

Hasilnya sama dengan fit kurva, karena fit kurva memang mengestimasi α yang
sama.

## Data mentah
- `hw_20261111_211151_sudut_-10_lalu_didiamkan_2_detik.csv`
  (tahan −10° lalu lepas; gerak < 0,5° → tidak dipakai untuk b)
- `hw_20261111_211524_diam_di_0_lalu_diberi_gangguan.csv`
  (dua gangguan: t≈2 s ke −4,8°; t≈9 s ke +14,4°) → dipakai untuk b

| Berkas | Durasi | Laju | Catatan |
|---|---|---|---|
| hw_20261111_211151 | 6,78 s | ~138 Hz | gerak terlalu kecil |
| hw_20261111_211524 | 14,15 s | ~136 Hz | dipakai |

## Hasil fit (berdasarkan hw_20261111_211524)

| Event | α (1/s) | Periode (s) | R² | b = 0,0280·α (N·m·s/rad) |
|---|---|---|---|---|
| Dorongan 1 (−4,8°) | 1,3378 ± 0,0342 | 4,54 | 0,922 | 0,03746 ± 0,00096 |
| Dorongan 2 (+14,4°) | 1,1335 ± 0,0160 | 5,40 | 0,969 | 0,03174 ± 0,00045 |

Penggabungan:
- Rata-rata biasa = 0,0346
- **Rata-rata berbobot (1/σ²) = 0,0328 ± 0,0004** ← dipakai sebagai `b = 0,033`

Event 2 lebih dipercaya (R² lebih tinggi); memakai event 2 saja memberi
b ≈ 0,032. Rentang wajar keseluruhan: **0,031 – 0,038**.

## Ketergantungan pada J (penting)

`b = 2·J·α` membutuhkan J. Dari gerak saja hanya rasio `b/J = 2α` yang
terukur — J dan b **tidak bisa dipisah** dari satu uji ayunan bebas. Karena itu
nilai b di sini memakai J hasil **hitungan tidak langsung** (massa + geometri),
bukan J yang diukur langsung. Akibatnya:

- b berskala **proporsional** terhadap J. Jika J bergeser 10%, b juga ~10%.
- Ketidakpastian terbesar b berasal dari J (±0,001 kg·m²), bukan dari fit.
- **Jangan** memasukkan b ini untuk "mencari J" — hasilnya hanya mengembalikan
  J0 yang dipakai, bukan nilai baru (melingkar).

Untuk J absolut yang independen (lalu b yang sepenuhnya valid), ukur J langsung:
- bandul bifilar: `J = T²·m·g·d² / (4π²·L)` (m, d, L, T diukur; tidak butuh b),
- atau tambah massa simetris, ukur α dua kali, lalu pisahkan J dari k.

Setelah J_ukur didapat, hitung ulang `b = 2·J_ukur·α` dengan α yang sama.

Estimasi ketidakpastian b saat ini: `b ≈ 0,033 ± 0,002 N·m·s/rad`
(σ_b ≈ √[(2α·σ_J)² + (2J·σ_α)²], σ_J ≈ 0,001).

## Catatan penting
- Data menunjukkan **ayunan teredam**, bukan luncuran monoton → ada torsi
  pemulih kecil (CoG sedikit di bawah poros, orde beberapa mm). Model di
  simulasi masih memakai `l = 0` (tanpa gravitasi), sehingga ini pendekatan.
- b terukur (motor mati) hanya mencakup gesekan poros; **redaman aerodinamis
  baling-baling saat berputar tidak termasuk** → b operasional bisa lebih besar.
- Nilai tebakan lama 0,02 terlalu kecil (~1,7× dari hasil ukur).
- `DEFAULT_GAINS` pada `sim_backend.py` dituning dengan b = 0,02, sehingga
  setelah b diganti perlu verifikasi/perapihan ulang gain PID.
