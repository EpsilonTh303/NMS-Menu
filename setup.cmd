@echo off
setlocal
cd /d "%~dp0"
python -m pip install --target vendor -r requirements-qt.txt
if errorlevel 1 (
    echo Qt kurulumu tamamlanamadi. Python 3.12 ve internet baglantisini kontrol edin.
    pause
    exit /b 1
)
echo Kurulum tamamlandi. start.cmd ile menuyu acabilirsiniz.
