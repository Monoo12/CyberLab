@echo off
rem ============================================================================
rem Lanzador de la app del visitante (Windows). Normalmente: doble clic.
rem En el MENU elegis Motor (Simulado/Real), Dificultad, Modo libre, Panel visual.
rem Flags opcionales (kiosco, saltea el menu):
rem   run-terminal.bat --autostart
rem   run-terminal.bat --autostart --engine real --difficulty medio
rem Instalacion: scripts\setup-terminal.bat   (equivalente Linux: run-terminal.sh)
rem ============================================================================
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -m app.main %*
  exit /b %errorlevel%
)
where py >nul 2>&1
if %errorlevel%==0 ( py -3 -m app.main %* ) else ( python -m app.main %* )
