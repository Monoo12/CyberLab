@echo off
rem ============================================================================
rem Control del FILE-SERVER (nodo vulnerable dockerizado) en Windows.
rem   on / start   encender (construye si hace falta)
rem   off / stop   apagar
rem   reset        reiniciar a estado limpio (entre visitantes)
rem   status       ver estado
rem   logs         ver logs en vivo (Ctrl+C para salir)
rem Instalacion inicial del equipo:  scripts\setup-fileserver.bat
rem Equivalente Linux: node/fileserver.sh
rem ============================================================================
setlocal
cd /d "%~dp0"

docker version >nul 2>&1
if errorlevel 1 ( echo [fileserver] Docker no responde. Abri Docker Desktop. & exit /b 1 )

set "ACTION=%~1"
if "%ACTION%"=="" set "ACTION=help"

if /i "%ACTION%"=="on"     ( docker compose up -d --build & echo [fileserver] ENCENDIDO & goto :done )
if /i "%ACTION%"=="start"  ( docker compose up -d --build & echo [fileserver] ENCENDIDO & goto :done )
if /i "%ACTION%"=="off"    ( docker compose down & echo [fileserver] APAGADO & goto :done )
if /i "%ACTION%"=="stop"   ( docker compose down & echo [fileserver] APAGADO & goto :done )
if /i "%ACTION%"=="reset"  ( docker compose down & docker compose up -d & echo [fileserver] reiniciado a estado limpio & goto :done )
if /i "%ACTION%"=="status" ( docker compose ps & goto :done )
if /i "%ACTION%"=="logs"   ( docker compose logs -f & goto :done )

echo uso: %~nx0 {on ^| off ^| reset ^| status ^| logs}
exit /b 1

:done
endlocal
