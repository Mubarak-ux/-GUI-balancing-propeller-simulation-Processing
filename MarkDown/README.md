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
6. **Launcher 1-Klik (`run_simulasi.bat`)**:
   - Sekali klik langsung membuka viewer Processing 3D dan GUI Python secara bersamaan.

---

## 🚀 Cara Menjalankan

### Cara 1: Menggunakan Launcher Otomatis (Paling Mudah)
* **Dari File Explorer**: Double-click file `run_simulasi.bat`.
* **Dari Terminal VS Code / PowerShell**:
  ```powershell
  .\run_simulasi.bat
  ```

### Cara 2: Manual
1. Buka file `BalancingPropellerViewer/BalancingPropellerViewer.pde` di aplikasi Processing, lalu klik tombol **Play (Run ▶)**.
2. Di terminal folder `VERSI 2`, jalankan:
   ```bash
   python run_sim.py
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

## 📁 Struktur Modul Proyek

### Python Backend & GUI (`app/`)
* **`app/main.py`**: Entry point dan inisialisasi aplikasi PySide6.
* **`app/main_window.py`**: Jendela utama, grafik telemetri, metrik respon, dan skenario otomatis.
* **`app/sim_backend.py`**: Model fisika mekanika dinamika seesaw 1-DOF dan algoritma PID.
* **`app/processing_stream.py`**: Pengirim telemetri UDP port 9999 dengan validasi ACK dua arah.
* **`app/metrics.py`**: Perhitungan metrik respon transien (*overshoot*, *rise time*, *settling time*, dll.).
* **`app/widgets/beam_view.py`**: Widget animasi 2D penyeimbang balok.
* **`app/widgets/controls.py`**: Komponen slider parameter, kartu metrik, dan tombol kontrol.

### Processing 3D Viewer (`BalancingPropellerViewer/`)
File skrip `.pde` telah dimodularisasi menjadi tab-tab terpisah di aplikasi Processing:
* **`BalancingPropellerViewer.pde`**: Setup utama, draw loop, dan variabel state telemetri global.
* **`Network.pde`**: Protokol komunikasi UDP socket, parsing JSON, balasan ACK, dan sinyal impuls.
* **`Camera.pde`**: Kontrol kamera orbit 3D, pencahayaan scene, lantai grid, serta event mouse & keyboard.
* **`Model.pde`**: Geometri 3D rakitan alat balancing propeller, baling-baling blur, panah gaya thrust, dan busur derajat.
* **`HUD.pde`**: Tampilan 2D overlay Heads-Up Display (informasi telemetri, status koneksi, dan notifikasi).
