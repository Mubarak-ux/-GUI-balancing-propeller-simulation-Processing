# Log Uji PID Hardware (18-11-2026)

F-max 15 % kecuali disebut lain. Data di folder `data/`.

| # | File | Gain Kp/Ki/Kd | Hasil | Temuan → perbaikan |
|---|---|---|---|---|
| 1 | `hw_20261118_171405_percobaanPID` | 3 / 1,5 / 1 | Osilasi ±3,6°, periode 1,1 s | Loop PID turun ke **25 Hz** (ledcWrite memblokir) → tulis ESC di task core 0, loop kembali 500 Hz. Getaran accel 0,21 g → filter τ 0,7 s, DLPF 21 Hz |
| – | (F-max 10 %) | – | Motor nyala, batang diam | Bias 11 % > F-max → koreksi 0. Bias jadi tengah rentang (8+Fmax)/2 |
| 2 | `hw_20261118_172326_testPID_2` | 1,5 / 0,6 / 1 | Motor kiri lambat, batang tertahan 14 s di +31° walau perintah 15/8 % | Desync start ESC → **soft-start** + pembatas laju 40 %/s. Integral windup → I-zone. Torsi tetap → **Trim** |
| 3 | `hw_20261118_175551_strat_trim` | 1,5 / 0,6 / 1 | Soft-start berhasil. Sp 0: std 2,9° → 2,2° setelah trim | – |
| 3b | `hw_20261118_175628_-10` | 1,5 / 0,6 / 1 | Overshoot 60 % (+10), ~100 % (−10), settling 6–8 s | Identifikasi: plant **tidak stabil** (k < 0) → Kp naik, I-zone 3° |
| 4 | `hw_20261118_180422_starttrimke2` | 2,5 / 2 / 1 | Sp 0: std 2,3° → 1,8° setelah trim (trim ≈ −13) | – |
| 4b | `hw_20261118_180513_-_10kedua` | 2,5 / 2 / 1 | **+10: rata 9,9°, std 0,45°**, overshoot 2,9°. −10: tertahan di −17° | I-zone 3° menahan integral saat \|e\| > 3° → I-zone 6°, gain robust 2 / 1,5 / 1 |

## Gain berikutnya untuk diuji

Kp 2,0 / Ki 1,5 / Kd 1,0, I-zone 6° (firmware), F-max 15 %.
Prosedur: start + trim di 0°, lalu step 0 → +10 → 0 → −10 → 0 (tiap 8 s).
