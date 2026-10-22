#!/usr/bin/env bash
set -e

APP_DIR="$HOME/.local/share/gemini-agent"
mkdir -p "$APP_DIR"

echo "===================================================="
echo "   Установка Gemini Desktop Agent (Linux)"
echo "===================================================="

if ! command -v mpv &>/dev/null || ! command -v git &>/dev/null || ! command -v python3 &>/dev/null; then
    echo "[*] Установка системных пакетов..."
    if command -v pacman &>/dev/null; then
        sudo pacman -S --needed --noconfirm mpv alsa-utils git python python-pip
    elif command -v apt &>/dev/null; then
        sudo apt update && sudo apt install -y mpv alsa-utils git python3 python3-venv python3-pip
    elif command -v dnf &>/dev/null; then
        sudo dnf install -y mpv alsa-utils git python3 python3-pip
    fi
fi

if [ -d "$APP_DIR/.git" ]; then
    echo "[*] Обновление файлов..."
    git -C "$APP_DIR" pull --quiet
else
    echo "[*] Скачивание приложения..."
    git clone --depth 1 --quiet https://github.com/romeo-180/gemini-windows-agent.git "$APP_DIR"
fi

cd "$APP_DIR"

if [ ! -d "venv" ]; then
    echo "[*] Создание виртуального окружения..."
    python3 -m venv venv
fi

echo "[*] Установка библиотек Python..."
./venv/bin/pip install --upgrade pip --quiet
./venv/bin/pip install -r requirements.txt --quiet

DESKTOP_ENTRY="[Desktop Entry]
Type=Application
Name=Gemini Agent
Comment=Голосовой системный помощник Gemini
Exec=$APP_DIR/venv/bin/python $APP_DIR/tray.py
Icon=system-help
Terminal=false
Categories=Utility;System;"

mkdir -p "$HOME/.local/share/applications"
mkdir -p "$HOME/.config/autostart"
echo "$DESKTOP_ENTRY" > "$HOME/.local/share/applications/gemini-agent.desktop"
echo "$DESKTOP_ENTRY" > "$HOME/.config/autostart/gemini-agent.desktop"
chmod +x "$HOME/.local/share/applications/gemini-agent.desktop"
chmod +x "$HOME/.config/autostart/gemini-agent.desktop"

pkill -f "tray.py" 2>/dev/null || true
nohup "$APP_DIR/venv/bin/python" "$APP_DIR/tray.py" >/dev/null 2>&1 &

echo "✅ Готово! Ярлык и автозапуск созданы, агент запущен в трее."
