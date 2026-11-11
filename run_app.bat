@echo off
title Launcher Aplikasi Balancing Propeller (VERSI 2)
echo ========================================================
echo   MENJALANKAN APLIKASI BALANCING PROPELLER (VERSI 2)
echo ========================================================
echo.

:: Pindah ke direktori tempat script ini berada
cd /d "%~dp0"

:: Cek keberadaan Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python tidak ditemukan di sistem PATH!
    echo Pastikan Python sudah terinstal dan ditambahkan ke PATH.
    echo.
    pause
    exit /b 1
)

:: Jalankan launcher utama Python (otomatis membuka 3D Viewer & GUI)
echo Menjalankan aplikasi Balancing Propeller...
python "%~dp0run_app.py" %*

if %errorlevel% neq 0 (
    echo.
    echo [INFO] Program selesai dengan kode error %errorlevel%.
    pause
)
