@echo off
echo ========================================
echo Building Pattern Cleaner Executable
echo ========================================

echo.
echo Step 1: Creating virtual environment...
python -m venv venv
if errorlevel 1 (
    echo ERROR: Failed to create venv
    pause
    exit /b 1
)

echo.
echo Step 2: Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo Step 3: Installing PyInstaller...
pip install pyinstaller
if errorlevel 1 (
    echo ERROR: Failed to install PyInstaller
    pause
    exit /b 1
)

echo.
echo Step 4: Building executable...
pyinstaller --onefile --windowed --name "PatternCleaner" --clean sgf-search-delete-by-pattern-app.py
if errorlevel 1 (
    echo ERROR: Build failed
    pause
    exit /b 1
)

echo.
echo ========================================
echo BUILD COMPLETE!
echo ========================================
echo.
echo Your executable is located at:
echo   dist\PatternCleaner.exe
echo.
pause
