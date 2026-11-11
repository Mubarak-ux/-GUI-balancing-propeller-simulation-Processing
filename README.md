# Simulasi Balancing Propeller 3D (VERSI 2 - Processing Upgraded)

Proyek simulasi sistem kendali dinamika **Balancing Propeller (1-DOF Seesaw)** untuk mata kuliah **PSKD**.  
Menggunakan representasi visual 3D **Processing (P3D)** yang sangat ringan menggantikan Blender, dipadukan dengan kontrol kendali PID dan analitik metrik respon waktu di Python (PySide6).

---

## 🌟 Fitur Baru di VERSI 2

1. **Panah Vektor Gaya Dorong 3D (*Thrust Vector Arrows*)**:
   - Panah 3D vertikal muncul di atas masing-masing motor.
   - Panjang dan warna panah membesar/mengecil secara *real-time* mengikuti besar gaya dorong $F_1$ dan $F_2$ dalam Newton.
2. **Efek Putaran Baling-baling Cepat (*Motion Blur Spinning Disc*)**:
   - Efek piringan transparan berkecepatan tinggi dengan lingkaran ujung kuning yang dinamis mengikuti RPM motor.
3. **Busur Derajat Sudut (*Angle Protractor Arc*) di Poros Tengah**:
   - Skala busur derajat 3D ($-30^\circ$ s/d $+30^\circ$, batas mekanik terukur) dengan jarum cyan penunjuk sudut aktual $\theta$ dan jarum amber penunjuk target *setpoint*.
4. **Pemicu Gangguan Impuls Fisik (*Disturbance Impulse*)**:
   - Menguji keandalan (*robustness*) PID saat batang ditabrak/disentak secara tiba-tiba:
     - **Klik Kiri pada Batang 2D**: Klik sisi kiri atau kanan batang di GUI Python.
     - **Tombol UI**: Klik tombol `💥 Sentak Gangguan (Impuls)`.
     - **Tombol Keyboard di Python**: Tekan tombol `D` atau `Shift+D`.
     - **Tombol Keyboard di Processing**: Klik jendela 3D dan tekan **[SPACE]**!
5. **Perhitungan Metrik Respon Transien Otomatis**:
   - Menghitung otomatis: *Overshoot %*, *Rise Time*, *Settling Time*, *Steady-State Error*, dan *Peak Time*.
6. **Launcher 1-Klik (`run_app.bat` / `run_app.py`)**:
   - Sekali klik langsung membuka viewer 3D (Processing) dan GUI Python (PySide6) secara bersamaan, mendukung mode Simulasi dan Hardware fisik.

---

## 📋 Prasyarat

- **Python 3.10+** (diuji pada 3.14)
- **Processing 4** (untuk viewer 3D) — https://processing.org/download
- *(Opsional)* Arduino Uno dengan firmware kating untuk mode Hardware

Install dependensi Python:

```bash
pip install -r requirements.txt
```

> `pyserial` hanya dibutuhkan untuk mode Hardware. Tanpa itu, aplikasi tetap
> bisa dijalankan pada mode Simulasi.

---

## 🚀 Cara Menjalankan

### Cara 1: Menggunakan Launcher Otomatis (Paling Mudah)
* **Dari File Explorer**: Double-click file `run_app.bat`.
* **Dari Terminal VS Code / PowerShell**:
   ```powershell
   .\run_app.bat
   ```
   *(atau `python run_app.py`)*

   Launcher default membuka **mode Simulasi**. Untuk langsung ke mode
   Hardware, jalankan `python run_app.py --mode hw`. Agar noise simulasi
   reproducible (mis. untuk laporan), tambahkan `--seed 42`.

### Cara 2: Manual
1. Buka file `BalancingPropellerIMU/BalancingPropellerIMU.pde` di aplikasi Processing, lalu klik tombol **Play (Run ▶)**.
2. Di terminal folder `VERSI 2`, jalankan:
   ```bash
   python run_app.py --no-3d
   ```

---

## 🎮 Kontrol Navigasi Kamera di Processing

| Kontrol | Aksi |
| :--- | :--- |
| **Klik Kiri + Geser** | Rotasi Orbit 3D (*natural / inverted*) |
| **Scroll Mouse** | Zoom In / Zoom Out |
| **Klik Kanan + Geser**| Pan / Geser Posisi Kamera |
| **Tombol `[SPACE]`** | **Sentak Gangguan Impuls ke Batang** |
| **Tombol `R`** | Reset Kamera ke Sudut Default |
| **Tombol `1`, `2`, `3`, `4`** | Tampak Depan, Samping, Atas, dan Bawah |
| **Tombol `H`** | Tampilkan / Sembunyikan HUD Info |

---

## 📁 Struktur Folder

```
VERSI 2/
├── app/                     # Kode Python (GUI & backend)
├── BalancingPropellerIMU/   # Sketch Processing 3D viewer (.pde)
├── docs/                    # Dokumentasi & catatan (lihat docs/README.md)
│   └── assets/              # Gambar pendukung (tampak atas/depan/…)
├── firmware/                # Backup firmware Arduino Uno (.hex)
├── data/                    # Hasil rekaman CSV (tidak di-commit)
├── run_app.py / run_app.bat # Launcher
├── requirements.txt
├── LICENSE
└── README.md
```

### Python Backend & GUI (`app/`)
* **`app/main.py`**: Entry point dan inisialisasi aplikasi PySide6.
* **`app/main_window.py`**: Jendela utama, grafik telemetri, metrik respon, dan skenario otomatis.
* **`app/sim_backend.py`**: Model fisika mekanika dinamika seesaw 1-DOF dan algoritma PID.
* **`app/processing_stream.py`**: Pengirim telemetri UDP port 9999 dengan validasi ACK dua arah.
* **`app/metrics.py`**: Perhitungan metrik respon transien (*overshoot*, *rise time*, *settling time*, dll.).
* **`app/widgets/beam_view.py`**: Widget animasi 2D penyeimbang balok.
* **`app/widgets/controls.py`**: Komponen slider parameter, kartu metrik, dan tombol kontrol.

### Processing 3D Viewer (`BalancingPropellerIMU/`)
Sketch `.pde` dimodularisasi menjadi beberapa tab di aplikasi Processing:
* **`BalancingPropellerIMU.pde`**: Setup utama, `draw()` loop, dan variabel state telemetri global.
* **`NetworkIMU.pde`**: Protokol komunikasi UDP socket, parsing JSON, balasan ACK, dan pengiriman sinyal impuls.
* **`CameraIMU.pde`**: Kontrol kamera orbit 3D, pencahayaan scene, lantai grid, serta event mouse & keyboard.
* **`ModelIMU.pde`**: Geometri 3D rakitan alat balancing propeller, baling-baling blur, panah gaya thrust, dan busur derajat.
* **`HudIMU.pde`**: Tampilan 2D overlay Heads-Up Display (informasi telemetri, status koneksi, dan notifikasi).

### Dokumentasi (`docs/`)
* **[`docs/README.md`](docs/README.md)**: Indeks seluruh dokumen & aset.
* **[`docs/ringkasan_pengukuran.md`](docs/ringkasan_pengukuran.md)**: Data terukur alat (massa, dimensi, J) & parameter simulasi.
* **[`docs/pengukuran_b.md`](docs/pengukuran_b.md)**: Identifikasi redaman `b` (uji ayunan, `b = 2·J·α`).
* **[`docs/versi2.md`](docs/versi2.md)**: Komparasi VERSI 1 vs VERSI 2.
