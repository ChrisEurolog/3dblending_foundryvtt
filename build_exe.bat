@echo off
setlocal enabledelayedexpansion
echo ======================================================
echo          chriseurolog3d: BUILD EXECUTABLE
echo ======================================================

:: Ensure we are in the correct directory (where this script is)
cd /d "%~dp0"

echo Checking for Python...
python --version
if %errorlevel% neq 0 (
    echo ❌ Python not found! Please install Python 3.10+ and add to PATH.
    pause
    exit /b
)

echo.
echo Installing PyInstaller...
python -m pip install pyinstaller
if %errorlevel% neq 0 (
    echo ❌ Failed to install PyInstaller.
    pause
    exit /b
)

echo.
echo Checking for source files...
if not exist "scripts\main_pipeline.py" (
    echo ❌ Error: scripts\main_pipeline.py not found!
    echo Please make sure you are running this batch file from the root of the repository.
    pause
    exit /b
)
if not exist "scripts\blender_worker.py" (
    echo ❌ Error: scripts\blender_worker.py not found!
    pause
    exit /b
)

echo.
echo Building chriseurolog3d.exe...
:: Bundles blender_worker.py into the root of the internal temp directory
:: Uses Windows backslashes for paths
python -m PyInstaller --clean --onefile --name chriseurolog3d --add-data "scripts\blender_worker.py;." "scripts\main_pipeline.py"

if %errorlevel% neq 0 (
    echo ❌ Build failed!
    pause
    exit /b
)

echo.
echo Copying configuration file...
if exist axiom_config.json (
    copy axiom_config.json dist\axiom_config.json
) else (
    echo ⚠️ Warning: axiom_config.json not found in root. Please copy it to dist\ manually.
)

echo.
echo ======================================================
echo ✅ Build Successful!
echo Executable is located in: dist\chriseurolog3d.exe
echo Configuration file is located in: dist\axiom_config.json
echo ======================================================
pause
