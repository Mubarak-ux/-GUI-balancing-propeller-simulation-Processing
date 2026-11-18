# Log Uji PID Hardware (18-11-2026)

F-max 15 % kecuali disebut lain. Data di folder `data/2026-11-18_uji_pid/`.

| # | File | Gain Kp/Ki/Kd | Hasil | Temuan → perbaikan |
|---|---|---|---|---|
| 1 | `hw_20261118_171405_percobaanPID` | 3 / 1,5 / 1 | Osilasi ±3,6°, periode 1,1 s | Loop PID turun ke **25 Hz** (ledcWrite memblokir) → tulis ESC di task core 0, loop kembali 500 Hz. Getaran accel 0,21 g → filter τ 0,7 s, DLPF 21 Hz |
| – | (F-max 10 %) | – | Motor nyala, batang diam | Bias 11 % > F-max → koreksi 0. Bias jadi tengah rentang (8+Fmax)/2 |
| 2 | `hw_20261118_172326_testPID_2` | 1,5 / 0,6 / 1 | Motor kiri lambat, batang tertahan 14 s di +31° walau perintah 15/8 % | Desync start ESC → **soft-start** + pembatas laju 40 %/s. Integral windup → I-zone. Torsi tetap → **Trim** |
| 3 | `hw_20261118_175551_strat_trim` | 1,5 / 0,6 / 1 | Soft-start berhasil. Sp 0: std 2,9° → 2,2° setelah trim | – |
| 3b | `hw_20261118_175628_-10` | 1,5 / 0,6 / 1 | Overshoot 60 % (+10), ~100 % (−10), settling 6–8 s | Identifikasi: plant **tidak stabil** (k < 0) → Kp naik, I-zone 3° |
| 4 | `hw_20261118_180422_starttrimke2` | 2,5 / 2 / 1 | Sp 0: std 2,3° → 1,8° setelah trim (trim ≈ −13) | – |
| 4b | `hw_20261118_180513_-_10kedua` | 2,5 / 2 / 1 | **+10: rata 9,9°, std 0,45°**, overshoot 2,9°. −10: tertahan di −17° | I-zone 3° menahan integral saat \|e\| > 3° → I-zone 6°, gain robust 2 / 1,5 / 1 |

| 5 | `hw_20261118_181415_trimke3` | 2 / 1,5 / 1 | Sp 0: std 1,8° (sebelum trim) / 2,4° (sesudah, trim ≈ −10) | Osilasi ~2° tidak berubah walau gain diganti → kemungkinan besar dari gangguan fisik (pusat massa, turbulensi), bukan gain |
| 5b | `hw_20261118_181451_-_10_ketiga` | 2 / 1,5 / 1 | +10: rata 10,7°, std 2,1°, overshoot 5,9°. **−10: tertahan di −22,4°** | Integral **mati** di luar I-zone 6° (error 12°) → integral di luar zona kini **diperlambat 50 %**, bukan dimatikan. Torsi jatuh sisi negatif lebih besar (perlu u ≈ +10 % di −22° vs −11 % di 0°) |
| 6 | `hw_20261118_182146_setpoint_-_10keempat` | 2 / 1,5 / 1 (integral 50 % di luar zona) | **−10 tercapai**: rata −9,1° (3 s terakhir), std 1,4°. +10: rata 10,6°, std 1,7°. Overshoot: +10 → 17,1°, −10 → −22,1°. Settling ~9 s | Error tunak teratasi. Sisa: overshoot besar (terutama sisi negatif) & goyangan ~1,5° → perbaikan fisik / uji Kp 2,5 |
| 7 | `hw_20261118_184438_-_10PID3_2_1` | **3 / 2 / 1** | 0: rata +0,3°, std 0,55°. **+10: rata 9,6°, std 0,40°, lewat 4,9°, tenang 2,3 s.** −10: rata −10,2°, std 0,76°, lewat 9,3°, masuk ±1,5° ~3 s. +20: rata 20,2°, std 0,51°, lewat 10,8°. −20 (step 40°): rata −19,8°, std 1,3°, sempat ke batas mekanik | **Gain terbaik sejauh ini** → jadi default. Sisa: overshoot sisi negatif & step besar (torsi jatuh sisi negatif) |

## Gain terpilih

Default GUI sekarang **Kp 3,0 / Ki 2,0 / Kd 1,0** (uji ke-7), I-zone 6° + integral 50 % di luar zona, F-max 15 %.
Prosedur: start + trim di 0°, lalu step 0 → +10 → 0 → −10 → 0 (tiap 8 s).
