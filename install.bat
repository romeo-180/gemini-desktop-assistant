@echo off
chcp 65001 >nul
title Установка Gemini Desktop Agent
echo ====================================================
echo       Установка Gemini Desktop Agent (Windows)
echo ====================================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ОШИБКА] Python не найден в системе!
    echo Установите Python 3 с официального сайта python.org
    echo Обязательно отметьте галочку "Add Python to PATH".
    pause
    exit /b
)

if not exist "venv" (
    echo [*] Создание виртуального окружения venv...
    python -m venv venv
)

echo [*] Установка зависимостей из requirements.txt...
call .\venv\Scripts\activate.bat
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

if not exist "gemini_key.txt" (
    echo.
    echo ----------------------------------------------------
    echo Файл ключа gemini_key.txt не найден.
    echo Получите бесплатный API ключ на: https://aistudio.google.com/
    echo.
    set /p USER_KEY="Вставьте ваш Gemini API ключ: "
    echo %USER_KEY%> gemini_key.txt
    echo [OK] Ключ сохранен в gemini_key.txt
    echo ----------------------------------------------------
    echo.
)

echo [*] Создание ярлыка на Рабочем столе...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $d = [Environment]::GetFolderPath('Desktop'); $s = $ws.CreateShortcut(\"$d\Gemini Agent.lnk\"); $s.TargetPath = (Resolve-Path '.\venv\Scripts\pythonw.exe'); $s.Arguments = 'tray.py'; $s.WorkingDirectory = (Get-Location).Path; $s.Description = 'Gemini Windows Agent'; $s.Save()"

echo.
echo ====================================================
echo          Установка успешно завершена!
echo Ярлык создан на рабочем столе. Запускаем агента...
echo ====================================================
start "" ".\venv\Scripts\pythonw.exe" "tray.py"
timeout /t 3 >nul
exit
