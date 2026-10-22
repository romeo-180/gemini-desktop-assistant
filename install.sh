#!/usr/bin/env bash
set -e

echo "===================================================="
echo "       Установка Gemini Desktop Agent (Linux)"
echo "===================================================="
echo ""

if ! command -v python3 &>/dev/null; then
    echo "[ОШИБКА] Python 3 не найден! Установите python3."
    exit 1
fi

if ! command -v mpv &>/dev/null; then
    echo "[*] Утилита mpv не найдена. Пробуем установить..."
    if command -v pacman &>/dev/null; then
        sudo pacman -S --needed --noconfirm mpv alsa-utils
    elif command -v apt &>/dev/null; then
        sudo apt update && sudo apt install -y mpv alsa-utils
    elif command -v dnf &>/dev/null; then
        sudo dnf install -y mpv alsa-utils
    fi
fi

if [ ! -d "venv" ]; then
    echo "[*] Создание виртуального окружения (venv)..."
    python3 -m venv venv
fi

echo "[*] Установка зависимостей Python..."
./venv/bin/pip install --upgrade pip --quiet
./venv/bin/pip install -r requirements.txt --quiet

if [ ! -f "gemini_key.txt" ]; then
    echo ""
    echo "----------------------------------------------------"
    echo "Файл gemini_key.txt не найден."
    echo "Получите ключ на: https://aistudio.google.com/"
    echo ""
    read -r -p "Вставьте ваш Gemini API ключ: " USER_KEY
    echo -n "$USER_KEY" > gemini_key.txt
    echo "[OK] Ключ сохранен в gemini_key.txt"
    echo "----------------------------------------------------"
    echo ""
fi

DESKTOP_DIR="$HOME/.local/share/applications"
mkdir -p "$DESKTOP_DIR"
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cat << DESKTOP_EOF > "$DESKTOP_DIR/gemini-agent.desktop"
[Desktop Entry]
Type=Application
Name=Gemini Agent
Comment=Gemini Desktop System Voice Agent
Exec=$APP_DIR/venv/bin/python $APP_DIR/tray.py
Icon=system-help
Terminal=false
Categories=Utility;
DESKTOP_EOF
chmod +x "$DESKTOP_DIR/gemini-agent.desktop"
echo "[*] Ярлык добавлен в меню приложений."

echo ""
echo "===================================================="
echo "          Установка успешно завершена!"
echo "Запускаем агента в фоне..."
echo "===================================================="

pkill -f "tray.py" 2>/dev/null || true
nohup "$APP_DIR/venv/bin/python" "$APP_DIR/tray.py" >/dev/null 2>&1 &
echo "✓ Агент запущен и находится в трее!"
