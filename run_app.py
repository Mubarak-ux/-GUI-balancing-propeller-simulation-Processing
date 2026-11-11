"""
Launcher Utama Aplikasi Balancing Propeller (VERSI 2 - Simulasi & Hardware).

Menjalankan sketch Processing BalancingPropellerIMU (tampilan 3D responsif HiDPI)
lalu membuka GUI Python PySide6. Pengguna dapat berganti antara mode Simulasi
dan mode Hardware langsung melalui dropdown "Sumber Data" di GUI.

Jalankan di terminal:
    python run_app.py              # sketch 3D langsung RUN + GUI
    python run_app.py --editor     # sketch hanya dibuka di editor Processing
    python run_app.py --no-3d      # GUI Python saja
    python run_app.py --mode sim   # GUI langsung terbuka di mode Simulasi
"""

import argparse
import os
import socket
import subprocess
import sys
import tempfile
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SKETCH_DIR = os.path.join(BASE_DIR, "BalancingPropellerIMU")
PDE_PATH = os.path.join(SKETCH_DIR, "BalancingPropellerIMU.pde")
PROCESSING_EXE = r"C:\Program Files\Processing\Processing.exe"
BUILD_DIR = os.path.join(tempfile.gettempdir(), "BalancingPropellerIMU_build")
UDP_PORT = 9999


def udp_port_free(port):
    """True jika belum ada program yang memakai port UDP 9999."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.bind(("0.0.0.0", port))
        return True
    except OSError:
        return False
    finally:
        s.close()


def start_processing(editor_only):
    if not os.path.exists(PDE_PATH):
        print(f"[PERINGATAN] Sketch tidak ditemukan: {PDE_PATH}")
        return
    if not os.path.exists(PROCESSING_EXE):
        print("[INFO] Processing.exe tidak ditemukan di C:\\Program Files\\Processing.")
        print("       Buka BalancingPropellerIMU.pde secara manual lalu tekan Run.")
        return
    if not udp_port_free(UDP_PORT):
        print(f"[PERINGATAN] Port UDP {UDP_PORT} sudah dipakai program lain.")
        print("       Kemungkinan Viewer 3D sebelumnya masih berjalan di background.")
        print("       Tutup dulu viewer tersebut jika ingin membuka baru.")
        return

    try:
        if editor_only:
            print("[1/2] Membuka BalancingPropellerIMU di editor Processing (tekan Run)...")
            subprocess.Popen([PROCESSING_EXE, PDE_PATH])
        else:
            print("[1/2] Menjalankan BalancingPropellerIMU (tampilan 3D)...")
            os.makedirs(BUILD_DIR, exist_ok=True)
            subprocess.Popen(
                [PROCESSING_EXE, "cli", f"--sketch={SKETCH_DIR}",
                 f"--output={BUILD_DIR}", "--force", "--run"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            print("      (kompilasi sketch butuh beberapa detik; jendela 3D muncul sendiri)")
        time.sleep(2)
    except Exception as exc:
        print(f"[PERINGATAN] Gagal membuka Processing otomatis: {exc}")
        print("       Buka BalancingPropellerIMU.pde secara manual lalu tekan Run.")


def run_gui(initial_mode="hw"):
    print("[2/2] Menjalankan GUI Python...")
    from PySide6 import QtWidgets

    from app.main import run
    from app.main_window import MainWindow

    original_init = MainWindow.__init__

    def init_with_mode(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        if initial_mode == "hw":
            i = self.cb_mode.findData("hw")
            if i >= 0:
                self.cb_mode.setCurrentIndex(i)
            # pilih otomatis port yang terlihat seperti Arduino/USB
            for k in range(self.cb_port.count()):
                text = self.cb_port.itemText(k).lower()
                if any(s in text for s in ("arduino", "ch340", "usb serial", "usb-serial")):
                    self.cb_port.setCurrentIndex(k)
                    break
            else:
                self.cb_port.insertItem(0, "(pilih port Uno — colok USB lalu ↻)", None)
                self.cb_port.setCurrentIndex(0)
        else:
            i = self.cb_mode.findData("sim")
            if i >= 0:
                self.cb_mode.setCurrentIndex(i)

    MainWindow.__init__ = init_with_mode
    return run()


def main():
    ap = argparse.ArgumentParser(description="Launcher Aplikasi Balancing Propeller (Simulasi & Hardware)")
    ap.add_argument("--editor", action="store_true",
                    help="buka sketch di editor Processing saja (tidak langsung Run)")
    ap.add_argument("--no-3d", action="store_true",
                    help="jangan buka Processing, GUI saja")
    ap.add_argument("--mode", choices=["hw", "sim"], default="hw",
                    help="mode awal saat GUI dibuka: 'hw' (Hardware) atau 'sim' (Simulasi), default: hw")
    args = ap.parse_args()

    os.chdir(BASE_DIR)
    if BASE_DIR not in sys.path:
        sys.path.insert(0, BASE_DIR)

    if not args.no_3d:
        start_processing(args.editor)
    else:
        print("[1/2] Processing dilewati (--no-3d)")

    print()
    print("  Mode dapat diubah kapan saja di GUI pada kartu 'Sumber Data' (Simulasi / Hardware).")
    print("  Jika mode Hardware: pilih port Uno -> Connect -> tunggu +-7 s (Uno menyiapkan ESC).")
    print()
    return run_gui(initial_mode=args.mode)


if __name__ == "__main__":
    sys.exit(main())
