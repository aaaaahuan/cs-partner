@echo off
echo Check Python environment...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed or not in PATH. Please install Python 3.8+ from https://www.python.org/
    pause
    exit /b
)

echo Installing dependencies (if needed)...
pip install -r requirements.txt

echo Starting CS2 Partner...
python main.py
pause
