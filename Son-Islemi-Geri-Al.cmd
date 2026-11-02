@echo off
echo Son filo islemi ONCESINDEKI iki oyun kaydi geri yuklenecek.
echo Sonraki ilerleme eski kayitta bulunmaz; guncel kayitlar ayrica yedeklenir.
echo Once oyundan tamamen cikin.
choice /C EH /N /M "Geri yuklensin mi? [E/H]: "
if errorlevel 2 exit /b
python "%~dp0fleet.py" restore-last
pause
