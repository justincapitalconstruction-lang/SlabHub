@echo off
echo Stopping existing SlabHub server...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    echo Killing process %%a
    taskkill /F /PID %%a 2>nul
)

timeout /t 2 /nobreak >nul

echo Starting SlabHub server...
cd /d "c:\Users\Justi\.zenflow\worktrees\new-task-4426\backend"
start "SlabHub Server" python app/main.py

echo Server restarting...
timeout /t 3 /nobreak >nul

echo.
echo Server should be running at http://localhost:8000
echo Check http://localhost:8000/health to verify
echo.
