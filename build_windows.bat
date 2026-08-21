@echo off
REM ==============================================================================
REM Build Script for Backend Development IDE on Windows (Standalone EXE)
REM ==============================================================================

echo [1/3] Sincronizando dependencias con uv...
uv sync --all-extras
if errorlevel 1 (
    echo Error sincronizando dependencias. Asegurate de tener uv instalado.
    pause
    exit /b 1
)

echo.
echo [2/3] Empaquetando aplicacion con PyInstaller...
uv run pyinstaller backend_ide.spec --noconfirm --clean
if errorlevel 1 (
    echo Error durante el empaquetado con PyInstaller.
    pause
    exit /b 1
)

echo.
echo [3/3] Construccion completada exitosamente!
echo Ejecutable generado en: dist\BackendDevelopmentIDE\BackendDevelopmentIDE.exe
echo.
pause
