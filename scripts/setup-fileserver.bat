@echo off
rem ============================================================================
rem Cyber Lab - instalacion del FILE-SERVER (nodo vulnerable) en Windows.
rem
rem Construye y levanta el contenedor Docker (Flask vulnerable + SSH) y verifica
rem que REALMENTE responda (contenedor + web :80 + usuario ctf). Requiere Docker
rem Desktop instalado y corriendo en modo Linux containers. El equivalente Linux
rem es scripts/setup-fileserver.sh.
rem
rem   Uso:  scripts\setup-fileserver.bat
rem ============================================================================
setlocal EnableDelayedExpansion

pushd "%~dp0.."
set "ROOT=%CD%"
popd
set "COMPOSE=%ROOT%\node\docker-compose.yml"

echo.
echo [cyberlab] FILE-SERVER (nodo) - repo en: %ROOT%
echo.

rem --- Docker disponible? ---
docker version >nul 2>&1
if errorlevel 1 (
  echo [cyberlab] ERROR: Docker no responde.
  echo    Instala Docker Desktop y abrilo ^(modo Linux containers^):
  echo    https://www.docker.com/products/docker-desktop/
  exit /b 1
)

rem --- Puertos 80 / 2222 ocupados en el host? (solo aviso) ---
for %%P in (80 2222) do (
  netstat -ano -p tcp 2>nul | findstr /c:":%%P " >nul && echo [cyberlab] AVISO: el puerto %%P figura en uso en el host ^(el nodo publica 80 y 2222^).
)

echo [cyberlab] Construyendo y levantando el FILE-SERVER ...
docker compose -f "%COMPOSE%" up -d --build
if errorlevel 1 (
  echo [cyberlab] ERROR al construir/levantar. Causas comunes:
  echo    - Puerto 80 ^(web^) o 2222 ^(SSH^) ocupado en el host.
  echo    - Sin internet la 1ra vez ^(baja la imagen base y los paquetes pip^).
  echo    - Docker Desktop en modo Windows containers ^(cambialo a Linux containers^).
  exit /b 1
)

echo [cyberlab] Verificando que el nodo responda ...
rem darle un momento a Flask / sshd / seed_db (~4 s)
ping -n 5 127.0.0.1 >nul

set "NODE_OK=1"
set "RUNNING="
for /f "delims=" %%R in ('docker inspect -f "{{.State.Running}}" cyberlab-fileserver 2^>nul') do set "RUNNING=%%R"
if "!RUNNING!"=="true" ( echo    [OK] contenedor cyberlab-fileserver corriendo ) else ( echo    [x] el contenedor NO quedo corriendo -^> node\fileserver.bat logs & set "NODE_OK=0" )

powershell -NoProfile -Command "try { Invoke-WebRequest -UseBasicParsing http://localhost:80/ -TimeoutSec 5 ^| Out-Null; exit 0 } catch { exit 1 }"
if errorlevel 1 ( echo    [x] la web NO responde en :80 -^> revisa logs y que el 80 este libre & set "NODE_OK=0" ) else ( echo    [OK] web responde en http://localhost:80 )

docker exec cyberlab-fileserver id ctf >nul 2>&1
if errorlevel 1 ( echo    [x] falta el usuario ctf -^> ls/read por SSH fallaran & set "NODE_OK=0" ) else ( echo    [OK] usuario ctf existe en el contenedor )

echo.
if "!NODE_OK!"=="1" (
  echo [cyberlab] Nodo verificado OK. En config.toml de la TERMINAL: [fileserver].ssh_port = 2222
) else (
  echo [cyberlab] Nodo con avisos: resolvelos ANTES del evento ^(node\fileserver.bat logs^).
)
echo    Control:  node\fileserver.bat  on ^| off ^| reset ^| status ^| logs
echo.
endlocal
