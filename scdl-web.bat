@echo off
rem Lanza la interfaz local de scdl. La primera vez crea un entorno virtual en .venv
rem e instala scdl en modo editable. "scdl-web.bat --update" fuerza reinstalar dependencias.
setlocal
cd /d "%~dp0"

set "PY=.venv\Scripts\python.exe"
set "STAMP=.venv\.scdl-web-installed"

if not exist "%PY%" (
    echo [scdl-web] Creando entorno virtual en .venv ...
    py -3 -m venv .venv 2>nul || python -m venv .venv
    if not exist "%PY%" (
        echo [scdl-web] No se encontro Python 3.10+. Instalalo desde https://www.python.org/downloads/
        pause
        exit /b 1
    )
)

if /i "%~1"=="--update" (
    del "%STAMP%" 2>nul
    shift
)

if not exist "%STAMP%" (
    echo [scdl-web] Instalando dependencias ...
    "%PY%" -m pip install --disable-pip-version-check -q -U -e . || (pause & exit /b 1)
    echo ok> "%STAMP%"
)

where ffmpeg >nul 2>nul || echo [scdl-web] AVISO: ffmpeg no esta en el PATH; es necesario para convertir y etiquetar.

"%PY%" -m scdl.web %1 %2 %3 %4
if errorlevel 1 pause
