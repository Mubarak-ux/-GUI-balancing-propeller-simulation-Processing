"""
Launcher Lengkap Simulasi Balancing Propeller (VERSI 2).
Membuka Processing 3D Viewer dan GUI Python sekaligus.

Jalankan di terminal:
    python run_simulasi.py
"""

import os
import subprocess
import sys
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PDE_PATH = os.path.join(BASE_DIR, "BalancingPropellerViewer", "BalancingPropellerViewer.pde")
PROCESSING_EXE = r"C:\Program Files\Processing\Processing.exe"

# 1. Buka Processing 3D Viewer
if os.path.exists(PROCESSING_EXE) and os.path.exists(PDE_PATH):
    print("[1/2] Membuka Processing 3D Viewer...")
    try:
        subprocess.Popen([PROCESSING_EXE, PDE_PATH])
        time.sleep(2)
    except Exception as e:
        print(f"[PERINGATAN] Gagal membuka Processing otomatis: {e}")
else:
    print("[INFO] Silakan buka BalancingPropellerViewer.pde di aplikasi Processing.")

# 2. Jalankan GUI Simulasi Python
print("[2/2] Menjalankan GUI Simulasi Python...")
from app.main import run

if __name__ == "__main__":
    sys.exit(run())
