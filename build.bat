@echo off
echo Check Python environment...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed or not in PATH. Please install Python 3.8+ from https://www.python.org/
    pause
    exit /b
)

echo Installing dependencies...
echo Using Tsinghua Mirror for faster download...
python -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple
python -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
python -m pip install pyinstaller -i https://pypi.tuna.tsinghua.edu.cn/simple

if %errorlevel% neq 0 (
    echo Failed to install dependencies!
    pause
    exit /b
)

echo Cleaning up old builds...
rmdir /s /q build dist
del /q *.spec

echo Building Executable...
echo Note: This might take a few minutes.
python -m PyInstaller --noconsole --onefile --name "CS2Partner" main.py

if %errorlevel% neq 0 (
    echo Build failed!
    pause
    exit /b
)

echo ========================================
echo Build Success!
echo The executable is located at: dist\CS2Partner.exe
echo You can now send this file to your users.
echo ========================================
pause
