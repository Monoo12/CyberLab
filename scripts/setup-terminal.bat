@echo off
rem ============================================================================
rem Cyber Lab - instalacion del dispositivo TERMINAL (PC del visitante) en Windows.
rem
rem Crea el entorno virtual, instala las dependencias de la app, deja config.toml
rem y usa el lanzador run-terminal.bat. Requiere Python 3.11+ ya instalado
rem (python.org, con tcl/tk). El equivalente Linux es scripts/setup-terminal.sh.
rem
rem   Uso:  doble clic, o en una consola:  scripts\setup-terminal.bat
rem ============================================================================
setlocal

rem --- raiz del repo (carpeta padre de este script) ---
pushd "%~dp0.."
set "ROOT=%CD%"
popd
cd /d "%ROOT%"

echo.
echo [cyberlab] Instalando la TERMINAL en: %ROOT%
echo.

rem --- Python disponible? (preferimos el launcher 'py', si no 'python') ---
set "PY="
py -3 --version >nul 2>&1 && set "PY=py -3"
if not defined PY ( python --version >nul 2>&1 && set "PY=python" )
if not defined PY (
  echo [cyberlab] ERROR: no encontre Python 3.
  echo    Instalalo desde https://www.python.org/downloads/windows/
  echo    En el instalador marca "Add python.exe to PATH" y deja tcl/tk ^(Tkinter^).
  exit /b 1
)
echo [cyberlab] Python detectado:
%PY% --version

rem --- entorno virtual ---
if not exist ".venv\Scripts\python.exe" (
  echo [cyberlab] Creando entorno virtual .venv ...
  %PY% -m venv .venv
  if errorlevel 1 ( echo [cyberlab] ERROR creando el venv. & exit /b 1 )
)
set "VPY=%ROOT%\.venv\Scripts\python.exe"

echo [cyberlab] Instalando dependencias de la app ...
"%VPY%" -m pip install --upgrade pip
"%VPY%" -m pip install -r requirements.txt
if errorlevel 1 ( echo [cyberlab] ERROR instalando requirements. & exit /b 1 )

rem --- config.toml (no se versiona; se crea desde la plantilla) ---
if not exist "config.toml" (
  copy /y "config.example.toml" "config.toml" >nul
  echo [cyberlab] config.toml creado desde la plantilla ^(ajusta IPs/credenciales para modo real^).
)

echo.
echo [cyberlab] LISTO. La terminal quedo instalada.
echo    Arrancar:          run-terminal.bat             ^(en el MENU elegis Simulado/Real, dificultad^)
echo    Kiosco ^(sin menu^): run-terminal.bat --autostart
echo.
echo    Para MODO REAL en Windows:
echo      - Instala nmap con Npcap:  https://nmap.org/download.html  ^(y corre la app como administrador^).
echo      - Necesitas un navegador ^(Edge/Chrome^) para el paso 'connect'.
echo      - Para los LEDs: conecta el micro por USB y pone el COM en config.toml ^([serial].port^).
echo      - El FILE-SERVER publica su SSH en el puerto 2222: config.toml ya trae ssh_port = 2222.
echo.
endlocal
