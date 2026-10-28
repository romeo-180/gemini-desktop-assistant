$ErrorActionPreference = "Stop"
$repoUrl = "https://github.com/romeo-180/gemini-desktop-assistant.git"
$installDir = "$HOME\gemini-agent"

Write-Host "===> Установка Gemini Desktop Assistant..." -ForegroundColor Cyan

# Проверка наличия Git и Python
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "Ошибка: Git не установлен. Установите Git и повторите попытку." -ForegroundColor Red
    exit 1
}
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Ошибка: Python не установлен. Установите Python и добавьте его в PATH." -ForegroundColor Red
    exit 1
}

# Клонирование или обновление
if (Test-Path $installDir) {
    Write-Host "Папка уже существует, обновляем репозиторий..." -ForegroundColor Yellow
    Set-Location $installDir
    git pull origin main
} else {
    Write-Host "Клонируем репозиторий..." -ForegroundColor Yellow
    git clone $repoUrl $installDir
    Set-Location $installDir
}

# Настройка виртуального окружения
if (-not (Test-Path "venv")) {
    Write-Host "Создание виртуального окружения (venv)..." -ForegroundColor Yellow
    python -m venv venv
}

Write-Host "Установка зависимостей..." -ForegroundColor Yellow
& ".\venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\venv\Scripts\pip.exe" install -r requirements.txt

Write-Host "`nУстановка завершена успешно!" -ForegroundColor Green
Write-Host "Запуск: cd $installDir; .\venv\Scripts\python.exe main.py" -ForegroundColor Cyan
