# Dokumentasi

Folder ini berisi seluruh catatan teknis & laporan proyek. README utama
(instalasi, cara menjalankan, struktur kode) ada di **[`../README.md`](../README.md)**.

## Daftar dokumen

| Berkas | Isi |
|---|---|
| [`ringkasan_pengukuran.md`](ringkasan_pengukuran.md) | Data terukur alat: massa, dimensi, momen inersia J, parameter simulasi (`J`, `b`, `L`, `Fmax`, `τ`), dan daftar parameter yang belum diukur. |
| [`pengukuran_b.md`](pengukuran_b.md) | Identifikasi koefisien redaman `b`: metode uji ayunan, penurunan `b = 2·J·α`, hasil fit (α, R², b ± σ), serta ketergantungan b terhadap J. |
| [`versi2.md`](versi2.md) | Laporan komparasi VERSI 1 (Blender) vs VERSI 2 (Processing P3D) dan daftar fitur baru. |

## Aset

| Folder/Berkas | Isi |
|---|---|
| `assets/` | Gambar tampak alat (atas, bawah, depan, samping). |
| `dokumentasiPY.png` | Tangkapan layar GUI Python. |
| `dokumentasiPDE.png` | Tangkapan layar viewer Processing 3D. |
| `rumus_awal_momen_inersia.png` | Catatan rumus awal momen inersia. |
| `menghitung J.png` | Sketsa/kerja hitungan momen inersia J. |

## Parameter kunci (ringkas)

| Parameter | Nilai | Sumber |
|---|---|---|
| `L` (poros → propeller) | 0,25 m | terukur |
| `J0` (momen inersia) | 0,0140 kg·m² | hitungan massa + geometri |
| `b` (redaman poros) | 0,033 ± 0,002 N·m·s/rad | uji ayunan (motor mati) |
| `stop` (batas mekanik) | ±30° | terukur |
| `Fmax` (thrust maks) | 8 N | asumsi (belum dikalibrasi) |
| `tau` (lag motor) | 0,10 s | asumsi (belum diukur) |

> Catatan: `b` berskala proporsional terhadap `J`. Untuk `b` yang sepenuhnya
> independen, `J` perlu diukur langsung (bandul bifilar / tambah massa simetris),
> lalu hitung ulang `b = 2·J·α`. Detail di [`pengukuran_b.md`](pengukuran_b.md).
