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
BUILD_DIR = os.path.join(tempfile.gettempdir(), "BalancingPropellerIMU_build")
UDP_PORT = 9999


def _candidate_processing_paths():
    """Lokasi umum executable Processing di berbagai OS/instalasi."""
    if sys.platform.startswith("win"):
        names = ("Processing.exe", "processing.exe")
        roots = [
            os.environ.get("PROCESSING_EXE"),
            os.environ.get("PROCESSING_HOME"),
            r"C:\Program Files\Processing",
            r"C:\Program Files (x86)\Processing",
            os.path.expandvars(r"%LOCALAPPDATA%\Processing"),
            os.path.expandvars(r"%ProgramFiles%\Processing-4"),
        ]
    elif sys.platform == "darwin":
        names = ("Processing",)
        roots = [
            os.environ.get("PROCESSING_EXE"),
            "/Applications/Processing.app/Contents/MacOS",
        ]
    else:
        names = ("processing",)
        roots = [
            os.environ.get("PROCESSING_EXE"),
            "/usr/bin",
            "/usr/local/bin",
            "/opt/processing",
            os.path.expanduser("~/Applications"),
        ]

    for root in roots:
        if not root:
            continue
        if os.path.isfile(root) and os.path.basename(root) in names:
            yield root
            continue
        if not os.path.isdir(root):
            continue
        try:
            entries = os.listdir(root)
        except OSError:
            continue
        # Processing 3/4 kadang berada dalam subfolder versi (mis. Processing-4.3)
        for name in entries:
            sub = os.path.join(root, name)
            if os.path.isdir(sub):
                for exe in names:
                    cand = os.path.join(sub, exe)
                    if os.path.isfile(cand):
                        yield cand
        for exe in names:
            cand = os.path.join(root, exe)
            if os.path.isfile(cand):
                yield cand


def find_processing():
    """Cari executable Processing secara dinamis.

    Urutan: env var ``PROCESSING_EXE``/``PROCESSING_HOME``, lalu path
    instalasi umum. Return path pertama yang ada, atau None.
    """
    seen = set()
    for path in _candidate_processing_paths():
        norm = os.path.normcase(os.path.abspath(path))
        if norm in seen:
            continue
        seen.add(norm)
        if os.path.isfile(path):
            return path
    return None


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
    processing_exe = find_processing()
    if processing_exe is None:
        print("[INFO] Processing tidak ditemukan secara otomatis.")
        print("       Set variabel lingkungan PROCESSING_EXE ke path executable,")
        print("       atau buka BalancingPropellerIMU.pde manual lalu tekan Run.")
        return
    if not udp_port_free(UDP_PORT):
        print(f"[PERINGATAN] Port UDP {UDP_PORT} sudah dipakai program lain.")
        print("       Kemungkinan Viewer 3D sebelumnya masih berjalan di background.")
        print("       Tutup dulu viewer tersebut jika ingin membuka baru.")
        return

    try:
        if editor_only:
            print("[1/2] Membuka BalancingPropellerIMU di editor Processing (tekan Run)...")
            subprocess.Popen([processing_exe, PDE_PATH])
        else:
            print("[1/2] Menjalankan BalancingPropellerIMU (tampilan 3D)...")
            os.makedirs(BUILD_DIR, exist_ok=True)
            subprocess.Popen(
                [processing_exe, "cli", f"--sketch={SKETCH_DIR}",
                 f"--output={BUILD_DIR}", "--force", "--run"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            print("      (kompilasi sketch butuh beberapa detik; jendela 3D muncul sendiri)")
        time.sleep(2)
    except Exception as exc:
        print(f"[PERINGATAN] Gagal membuka Processing otomatis: {exc}")
        print("       Buka BalancingPropellerIMU.pde secara manual lalu tekan Run.")


def run_gui(initial_mode="sim", seed=None):
    print("[2/2] Menjalankan GUI Python...")
    from app.main import run
    return run(initial_mode=initial_mode, seed=seed)


def main():
    ap = argparse.ArgumentParser(description="Launcher Aplikasi Balancing Propeller (Simulasi & Hardware)")
    ap.add_argument("--editor", action="store_true",
                    help="buka sketch di editor Processing saja (tidak langsung Run)")
    ap.add_argument("--no-3d", action="store_true",
                    help="jangan buka Processing, GUI saja")
    ap.add_argument("--mode", choices=["hw", "sim"], default="sim",
                    help="mode awal saat GUI dibuka: 'hw' (Hardware) atau 'sim' (Simulasi), default: sim")
    ap.add_argument("--seed", type=int, default=None,
                    help="seed noise simulasi agar hasil reproducible (default: acak)")
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
    return run_gui(initial_mode=args.mode, seed=args.seed)


if __name__ == "__main__":
    sys.exit(main())
