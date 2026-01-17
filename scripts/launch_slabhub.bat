@echo off
rem Launch the SlabHub server (Windows)
rem Adjust the path below to point to your Python interpreter and start_services script
"%~dp0..\..\venv\Scripts\python.exe" "%~dp0\..\start_services.py"
pause
