@echo off¡¡
:start
main.exe
choice /t 30 /d y /n >nul
goto start