"""
Launcher Utama Aplikasi Balancing Propeller (VERSI 2 - Simulasi & Hardware).

Secara default launcher ini HANYA membuka GUI Python (PySide6). Viewer 3D
Processing bisa dibuka belakangan lewat tombol "Buka 3D" di header GUI,
atau langsung saat start dengan flag --3d.

Jalankan di terminal:
    python run_app.py              # GUI Python saja (tanpa 3D)
    python run_app.py --3d         # GUI + langsung jalankan viewer 3D
    python run_app.py --editor     # GUI + buka sketch di editor Processing
    python run_app.py --mode sim   # GUI langsung terbuka di mode Simulasi
"""

import argparse
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def run_gui(initial_mode="sim", seed=None):
    print("[GUI] Menjalankan GUI Python...")
    from app.main import run
    return run(initial_mode=initial_mode, seed=seed)


def main():
    ap = argparse.ArgumentParser(description="Launcher Aplikasi Balancing Propeller (Simulasi & Hardware)")
    ap.add_argument("--3d", dest="open_3d", action="store_true",
                    help="langsung jalankan viewer 3D Processing saat start "
                         "(default: 3D dibuka belakangan lewat tombol di GUI)")
    ap.add_argument("--editor", action="store_true",
                    help="buka sketch di editor Processing saja (tidak langsung Run)")
    ap.add_argument("--no-3d", action="store_true",
                    help="jangan buka Processing (default; dipertahankan untuk kompatibilitas)")
    ap.add_argument("--mode", choices=["hw", "sim"], default="sim",
                    help="mode awal saat GUI dibuka: 'hw' (Hardware) atau 'sim' (Simulasi), default: sim")
    ap.add_argument("--seed", type=int, default=None,
                    help="seed noise simulasi agar hasil reproducible (default: acak)")
    args = ap.parse_args()

    os.chdir(BASE_DIR)
    if BASE_DIR not in sys.path:
        sys.path.insert(0, BASE_DIR)

    want_3d = args.open_3d or args.editor
    if args.no_3d:
        want_3d = False

    if want_3d:
        from app.processing_launcher import start_processing
        ok, msg = start_processing(editor_only=args.editor)
        print(("[3D] " if ok else "[PERINGATAN] ") + msg)
    else:
        print("[3D] Viewer 3D tidak dibuka otomatis. "
              "Klik tombol 'Buka 3D' di GUI kapan saja.")

    print()
    print("  Mode dapat diubah kapan saja di GUI pada kartu 'Sumber Data' (Simulasi / Hardware).")
    print("  Jika mode Hardware: pilih port Uno -> Connect -> tunggu +-7 s (Uno menyiapkan ESC).")
    print()
    return run_gui(initial_mode=args.mode, seed=args.seed)


if __name__ == "__main__":
    sys.exit(main())
