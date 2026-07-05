@echo off
REM Build standalone Windows .exe
REM Requires: pip install pyinstaller

echo === STM32 Flash Tool — Windows Build ===

REM Check PyInstaller
where pyinstaller >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

echo Building...
pyinstaller ^
    --onefile ^
    --windowed ^
    --name "STM32-Flasher" ^
    --clean ^
    stm32_flasher.py

echo.
echo Done: dist\STM32-Flasher.exe
dir dist\STM32-Flasher.exe
