@echo off
echo ======================================================
echo          chriseurolog3d: BUILD EXECUTABLE
echo ======================================================

echo Checking for Python...
python --version
if %errorlevel% neq 0 (
    echo ❌ Python not found! Please install Python 3.10+ and add to PATH.
    pause
    exit /b
)

echo.
echo Installing PyInstaller...
pip install pyinstaller
if %errorlevel% neq 0 (
    echo ❌ Failed to install PyInstaller.
    pause
    exit /b
)

echo.
echo Building chriseurolog3d.exe...
:: Bundles blender_worker.py into the root of the internal temp directory
pyinstaller --clean --onefile --name chriseurolog3d --add-data "scripts/blender_worker.py;." scripts/main_pipeline.py

if %errorlevel% neq 0 (
    echo ❌ Build failed!
    pause
    exit /b
)

echo.
echo Copying configuration file...
copy axiom_config.json dist\axiom_config.json

echo.
echo ======================================================
echo ✅ Build Successful!
echo Executable is located in: dist\chriseurolog3d.exe
echo Configuration file is located in: dist\axiom_config.json
echo ======================================================
pause
