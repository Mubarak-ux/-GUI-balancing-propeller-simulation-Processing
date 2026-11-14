"""Peluncur Processing 3D viewer (BalancingPropellerIMU).

Modul ini dipakai bersama oleh ``run_app.py`` (launcher) dan tombol
"Buka 3D" di GUI, supaya logika pencarian & menjalankan Processing tidak
diduplikasi.
"""

import os
import socket
import subprocess
import tempfile
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKETCH_DIR = os.path.join(BASE_DIR, "BalancingPropellerIMU")
PDE_PATH = os.path.join(SKETCH_DIR, "BalancingPropellerIMU.pde")
BUILD_DIR = os.path.join(tempfile.gettempdir(), "BalancingPropellerIMU_build")
UDP_PORT = 9999


def _candidate_processing_paths():
    """Lokasi umum executable Processing di berbagai OS/instalasi."""
    import sys

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


def udp_port_free(port=UDP_PORT):
    """True jika belum ada program yang memakai port UDP 9999."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.bind(("0.0.0.0", port))
        return True
    except OSError:
        return False
    finally:
        s.close()


def viewer_responsive(timeout=0.6):
    """True jika viewer 3D Processing menjawab ACK di port UDP 9999.

    Dipakai untuk membedakan viewer yang memang sudah berjalan dari
    proses "zombie" yang masih memegang port tetapi tidak merespons.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(timeout)
    try:
        s.sendto(b'{"probe":1}', ("127.0.0.1", UDP_PORT))
        while True:
            data, _ = s.recvfrom(64)
            if data in (b"ack", b"impulse"):
                return True
    except OSError:
        return False
    finally:
        s.close()


def _kill_stale_viewers():
    """Bunuh proses Processing/java yang masih memegang port UDP 9999
    tetapi tidak merespons (macet/zombie). Return True jika ada yang
    dibunuh. Hanya berjalan di Windows; platform lain return False.
    """
    import sys
    if not sys.platform.startswith("win"):
        return False
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "(Get-NetUDPEndpoint -LocalPort %d -ErrorAction SilentlyContinue)."
             "OwningProcess" % UDP_PORT],
            capture_output=True, text=True, timeout=10,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except Exception:
        return False
    pids = {p.strip() for p in out.stdout.splitlines() if p.strip().isdigit()}
    killed = False
    for pid in pids:
        try:
            subprocess.run(["taskkill", "/PID", pid, "/F"],
                           capture_output=True, timeout=10,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            killed = True
        except Exception:
            pass
    return killed


def start_processing(editor_only=False, wait=True, force=False, kill_stale=True):
    """Jalankan sketch BalancingPropellerIMU.

    Return ``(ok, message)`` dengan ``ok`` bernilai:
      * ``True``  -> viewer dijalankan (atau sudah aktif);
      * ``False`` -> Processing tidak ditemukan/sketch tidak ada/gagal.

    ``wait`` True menahan (sleep) sebentar supaya launcher CLI tidak
    langsung lanjut; GUI memakai ``wait=False`` agar tidak membeku.

    Jika port UDP 9999 sudah dipakai: kalau viewer ternyata masih
    merespons ACK, dianggap sudah jalan (return True tanpa membuka
    proses baru). Jika tidak merespons ("zombie"), proses Processing/
    java yang memegang port dibunuh dulu (``kill_stale``) lalu viewer
    dijalankan ulang.
    """
    if not os.path.exists(PDE_PATH):
        return False, f"Sketch tidak ditemukan: {PDE_PATH}"
    processing_exe = find_processing()
    if processing_exe is None:
        return False, ("Processing tidak ditemukan secara otomatis. Set variabel "
                       "lingkungan PROCESSING_EXE, atau buka .pde manual lalu Run.")

    if not udp_port_free(UDP_PORT):
        if viewer_responsive():
            return True, "Viewer 3D sudah berjalan dan terhubung."
        if kill_stale and _kill_stale_viewers():
            # beri waktu OS melepas port
            for _ in range(20):
                if udp_port_free(UDP_PORT):
                    break
                time.sleep(0.1)
        if not udp_port_free(UDP_PORT) and not force:
            return False, (f"Port UDP {UDP_PORT} masih dipakai proses lain. Tutup "
                           "program yang memakai port tersebut, atau jalankan lagi "
                           "dengan opsi paksa.")

    try:
        if editor_only:
            subprocess.Popen([processing_exe, PDE_PATH])
            msg = "Membuka sketch di editor Processing (tekan Run)."
        else:
            os.makedirs(BUILD_DIR, exist_ok=True)
            subprocess.Popen(
                [processing_exe, "cli", f"--sketch={SKETCH_DIR}",
                 f"--output={BUILD_DIR}", "--force", "--run"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            msg = ("Menjalankan viewer 3D (kompilasi butuh beberapa detik; "
                   "jendela 3D muncul sendiri).")
        if wait:
            time.sleep(2)
    except Exception as exc:
        return False, f"Gagal membuka Processing: {exc}"
    return True, msg
