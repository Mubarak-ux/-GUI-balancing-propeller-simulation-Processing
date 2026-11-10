@echo off
title Launcher Simulasi Balancing Propeller (VERSI 2)
echo ========================================================
echo   MENJALANKAN SIMULASI BALANCING PROPELLER (VERSI 2)
echo ========================================================
echo.

:: Pindah ke direktori tempat script ini berada
cd /d "%~dp0"

:: 1. Buka Processing 3D Viewer
echo [1/2] Membuka Processing 3D Viewer...
if exist "C:\Program Files\Processing\Processing.exe" (
    start "" "C:\Program Files\Processing\Processing.exe" "%~dp0BalancingPropellerViewer\BalancingPropellerViewer.pde"
) else (
    echo [INFO] Processing.exe tidak ditemukan di C:\Program Files\Processing.
    echo Pastikan file BalancingPropellerViewer.pde sudah dibuka di aplikasi Processing.
)

:: Tunggu 2 detik
timeout /t 2 /nobreak >nul

:: 2. Jalankan GUI Simulasi Python
echo [2/2] Menjalankan GUI Simulasi Python...
python "%~dp0run_sim.py"
