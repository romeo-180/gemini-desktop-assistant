import sys, os, time, json, shutil, ctypes, io, wave, subprocess, re
import psutil
import sounddevice as sd
import numpy as np
import pygame
from PyQt6.QtWidgets import (QApplication, QSystemTrayIcon, QMenu, QWidget, 
                             QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit, 
                             QPushButton, QLabel)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QTimer
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QLinearGradient, QColor, QPainterPath, QAction
from google import genai
from google.genai import types

# === MULTILINGUAL & AUTO-VOICE MODULE (EN / RU) ===
import os as _os, sys as _sys

def _init_app_lang():
    lang_file = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "lang.txt")
    if _os.path.exists(lang_file):
        try:
            with open(lang_file, "r", encoding="utf-8") as f:
                val = f.read().strip().lower()
                if val in ("en", "ru"):
                    return val
        except Exception:
            pass
    try:
        from PyQt6.QtWidgets import QApplication, QMessageBox
        _app = QApplication.instance() or QApplication(_sys.argv)
        msg = QMessageBox()
        msg.setWindowTitle("Language / Язык")
        msg.setText("Choose your language / Выберите язык интерфейса:")
        btn_en = msg.addButton("🇺🇸 English", QMessageBox.ButtonRole.AcceptRole)
        btn_ru = msg.addButton("🇷🇺 Русский", QMessageBox.ButtonRole.ActionRole)
        msg.exec()
        chosen = "ru" if msg.clickedButton() == btn_ru else "en"
        with open(lang_file, "w", encoding="utf-8") as f:
            f.write(chosen)
        return chosen
    except Exception:
        return "en"

APP_LANG = _init_app_lang()

# 1. Автовыбор голоса озвучки (Русский -> Светлана, Английский -> Aria)
try:
    import edge_tts as _edge_tts
    _orig_comm_init = _edge_tts.Communicate.__init__
    def _smart_comm_init(self, text, voice="ru-RU-SvetlanaNeural", *args, **kwargs):
        has_cyrillic = any("а" <= ch.lower() <= "я" or ch.lower() == "ё" for ch in str(text))
        smart_voice = "ru-RU-SvetlanaNeural" if has_cyrillic else "en-US-AriaNeural"
        return _orig_comm_init(self, text, smart_voice, *args, **kwargs)
    _edge_tts.Communicate.__init__ = _smart_comm_init
except Exception:
    pass

# 2. Автоперевод кнопок, меню и подсказок Qt при выборе English
_EN_MAP = {
    "🎙 Сказать": "🎙 Speak",
    "🧹 Быстрая": "🧹 Fast Clean",
    "🔥 Глубокая": "🔥 Deep Clean",
    "👁 Экран": "👁 Screen",
    "Отправить": "Send",
    "Выход": "Exit",
    "Открыть": "Open",
    "Выключить звук": "Mute voice",
    "Включить звук": "Unmute voice",
    "Настройка Gemini API": "Gemini API Setup",
    "Для работы ассистента нужен бесплатный ключ Gemini API.": "A free Gemini API key is required for the assistant.",
    "🔑 Получить ключ бесплатно": "🔑 Get Free API Key",
    "Ввести ключ": "Enter Key",
    "Отмена": "Cancel",
    "Ввод API ключа": "Enter API Key",
    "Вставьте ваш Gemini API ключ (AIzaSy...):": "Paste your Gemini API key (AIzaSy...):"
}

def _tr_text(text):
    if APP_LANG != "en" or not isinstance(text, str):
        return text
    res = text
    for ru_k, en_v in _EN_MAP.items():
        if ru_k in res:
            res = res.replace(ru_k, en_v)
    return res

try:
    from PyQt6.QtWidgets import QPushButton, QLabel, QMenu, QSystemTrayIcon
    _orig_btn_init = QPushButton.__init__
    def _tr_btn_init(self, *args, **kwargs):
        args = tuple(_tr_text(a) for a in args)
        _orig_btn_init(self, *args, **kwargs)
    QPushButton.__init__ = _tr_btn_init

    _orig_btn_set = QPushButton.setText
    def _tr_btn_set(self, text):
        _orig_btn_set(self, _tr_text(text))
    QPushButton.setText = _tr_btn_set

    _orig_menu_add = QMenu.addAction
    def _tr_menu_add(self, *args, **kwargs):
        args = tuple(_tr_text(a) for a in args)
        return _orig_menu_add(self, *args, **kwargs)
    QMenu.addAction = _tr_menu_add
except Exception:
    pass
# === END MULTILINGUAL MODULE ===


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATS_FILE = os.path.join(BASE_DIR, "stats.json")
KEY_FILE = os.path.join(BASE_DIR, "gemini_key.txt")
ICON_FILE = os.path.join(BASE_DIR, "gemini_icon.png")
TEMP_AUDIO = os.path.join(os.environ.get("TEMP", BASE_DIR), "gemini_reply.mp3")
TEMP_SCREEN = os.path.join(os.environ.get("TEMP", BASE_DIR), "gemini_screen.png")

NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
pygame.mixer.init()

def ensure_gemini_icon():
    size = 128
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    gradient = QLinearGradient(0, 0, size, size)
    gradient.setColorAt(0.0, QColor(0, 210, 255))
    gradient.setColorAt(0.5, QColor(138, 43, 226))
    gradient.setColorAt(1.0, QColor(255, 64, 129))

    path = QPainterPath()
    path.moveTo(64, 1)
    path.quadTo(76, 52, 127, 64)
    path.quadTo(76, 76, 64, 127)
    path.quadTo(52, 76, 1, 64)
    path.quadTo(52, 52, 64, 1)

    painter.fillPath(path, gradient)
    painter.end()
    pixmap.save(ICON_FILE, "PNG")

    icon = QIcon()
    for s in [16, 20, 24, 32, 48, 64, 128]:
        icon.addPixmap(pixmap.scaled(s, s, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
    return icon

def get_api_key():
    if "GEMINI_API_KEY" in os.environ:
        return os.environ["GEMINI_API_KEY"]
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return None

def load_stats():
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception: pass
    return {"total_requests": 0, "prompt_tokens": 0, "candidates_tokens": 0, "cost_usd": 0.0}

def save_stats(stats):
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

def get_system_metrics():
    cpu_pct = psutil.cpu_percent(interval=None)
    mem = psutil.virtual_memory()
    used_gb = mem.used / (1024**3)
    total_gb = mem.total / (1024**3)
    ram_str = f"{mem.percent}% ({used_gb:.1f}/{total_gb:.1f} ГБ)"

    vram_str = "VRAM: ~512 МБ"
    try:
        import win32com.client
        wmi = win32com.client.GetObject("winmgmts:")
        for adapter in wmi.InstancesOf("Win32_VideoController"):
            vram_mb = int(adapter.AdapterRAM or 0) // (1024 * 1024)
            if vram_mb > 0:
                vram_str = f"VRAM: ~{vram_mb} МБ"
                break
    except Exception: pass

    stats = load_stats()
    usd = stats.get("cost_usd", 0.0)
    rub = usd * 95.0
    bal_str = f"${usd:.4f} (~{rub:.2f} ₽)"

    return {
        "cpu": f"{cpu_pct:.0f}%",
        "ram": ram_str,
        "vram": vram_str,
        "balance": bal_str,
        "requests": stats.get("total_requests", 0)
    }

# ==================== ПОТОК ОЧИСТКИ С ЖИВЫМ ОТЧЕТОМ ====================
class CleanWorker(QThread):
    progress_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(str)

    def __init__(self, deep: bool = False):
        super().__init__()
        self.deep = deep

    def run(self):
        mode_str = "Глубокая" if self.deep else "Быстрая"
        self.progress_signal.emit(f"<b>🧹 Запуск {mode_str.lower()} очистки системы...</b>")
        
        freed_bytes = 0
        empty_dirs_count = 0
        local_app = os.environ.get("LOCALAPPDATA", "")
        win_dir = os.environ.get("SystemRoot", "C:\\Windows")
        user_profile = os.environ.get("USERPROFILE", os.path.expanduser("~"))

        # Шаг 1: Temp и кэши
        self.progress_signal.emit("⏳ [1/6] Очистка временных файлов Temp, DxCache и CrashDumps...")
        clean_targets = [
            os.environ.get("TEMP", ""),
            os.path.join(win_dir, "Temp"),
            os.path.join(local_app, "CrashDumps"),
            os.path.join(local_app, "Microsoft", "Windows", "WER"),
            os.path.join(local_app, "D3DSCache"),
            os.path.join(local_app, "AMD", "DxCache"),
        ]

        if self.deep:
            self.progress_signal.emit("⏳ [2/6] Проверка SoftwareDistribution, Minidump и CBS...")
            clean_targets.extend([
                os.path.join(win_dir, "SoftwareDistribution", "Download"),
                os.path.join(win_dir, "Minidump"),
                os.path.join(win_dir, "Logs", "CBS"),
                os.path.join(local_app, "Microsoft", "WinGet", "Packages"),
            ])
            mem_dmp = os.path.join(win_dir, "MEMORY.DMP")
            if os.path.exists(mem_dmp):
                try:
                    freed_bytes += os.path.getsize(mem_dmp)
                    os.remove(mem_dmp)
                except Exception: pass

        for target in clean_targets:
            if target and os.path.exists(target):
                for root, dirs, files in os.walk(target, topdown=False):
                    for f in files:
                        try:
                            p = os.path.join(root, f)
                            sz = os.path.getsize(p)
                            os.remove(p)
                            freed_bytes += sz
                        except Exception: pass
                    if os.path.abspath(root) != os.path.abspath(target):
                        try:
                            if not os.listdir(root):
                                os.rmdir(root)
                                empty_dirs_count += 1
                        except Exception: pass

        # Шаг 3: Пустые папки в Загрузках
        downloads_path = os.path.join(user_profile, "Downloads")
        if os.path.exists(downloads_path):
            for root, dirs, _ in os.walk(downloads_path, topdown=False):
                if os.path.abspath(root) != os.path.abspath(downloads_path):
                    try:
                        if not os.listdir(root):
                            os.rmdir(root)
                            empty_dirs_count += 1
                    except Exception: pass

        # Шаг 4: Корзина и DNS
        self.progress_signal.emit("⏳ [3/6] Очистка корзины и сброс кэша DNS...")
        try:
            ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 7)
        except Exception: pass

        try:
            subprocess.run(["ipconfig", "/flushdns"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=NO_WINDOW)
        except Exception: pass

        # Шаг 5: Очистка кэша pip и winget (для глубокой)
        if self.deep:
            self.progress_signal.emit("⏳ [4/6] Очистка кэша пакетов pip...")
            try:
                subprocess.run([sys.executable, "-m", "pip", "cache", "purge"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=NO_WINDOW)
            except Exception: pass

            self.progress_signal.emit("⏳ [5/6] Запуск оптимизации компонентов Windows (DISM) в фоне...")
            try:
                subprocess.Popen(["dism.exe", "/online", "/cleanup-image", "/startcomponentcleanup", "/quiet", "/norestart"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=NO_WINDOW)
            except Exception: pass

        # Шаг 6: Сброс RAM
        self.progress_signal.emit("⏳ [6/6] Сброс неиспользуемых рабочих наборов RAM...")
        before_mem = psutil.virtual_memory().used
        try:
            for proc in psutil.process_iter(['pid']):
                try:
                    handle = ctypes.windll.kernel32.OpenProcess(0x001F0FFF, False, proc.info['pid'])
                    if handle:
                        ctypes.windll.psapi.EmptyWorkingSet(handle)
                        ctypes.windll.kernel32.CloseHandle(handle)
                except Exception: pass
        except Exception: pass
        after_mem = psutil.virtual_memory().used

        freed_ram_mb = max(0, (before_mem - after_mem) // (1024 * 1024))
        freed_disk_mb = freed_bytes // (1024 * 1024)

        dism_note = "<br>• Фоновый процесс DISM завершит очистку старых обновлений без нагрузки." if self.deep else ""
        result_text = f"<font color='#00e676'><b>✓ {mode_str} очистка завершена:</b></font><br>• Освобождено на диске: <b>+{freed_disk_mb} МБ</b><br>• Выгружено из RAM: <b>~{freed_ram_mb} МБ</b><br>• Удалено пустых папок: <b>{empty_dirs_count}</b>{dism_note}"
        self.finished_signal.emit(result_text)

# ==================== ОЗВУЧКА СВЕТЛАНОЙ ====================
class TTSWorker(QThread):
    def __init__(self, text, voice="ru-RU-SvetlanaNeural", enabled_check=None):
        super().__init__()
        self.text = text
        self.voice = voice
        self.enabled_check = enabled_check

    def run(self):
        if self.enabled_check and not self.enabled_check():
            return
        clean = re.sub(r'```[\s\S]*?```', ' [Блок кода опущен] ', self.text)
        clean = re.sub(r'<[^>]+>', '', clean)
        clean = re.sub(r'[*#_`>~]', '', clean)
        clean = re.sub(r'https?://\S+', '', clean).strip()
        if not clean:
            return

        if os.path.exists(TEMP_AUDIO):
            try: os.remove(TEMP_AUDIO)
            except Exception: pass

        cmd = [sys.executable, "-m", "edge_tts", "--voice", self.voice, "--text", clean[:1200], "--write-media", TEMP_AUDIO]
        res = subprocess.run(cmd, capture_output=True, timeout=15, creationflags=NO_WINDOW)
        if res.returncode == 0 and os.path.exists(TEMP_AUDIO):
            if self.enabled_check and not self.enabled_check():
                return
            try:
                pygame.mixer.music.load(TEMP_AUDIO)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    if self.enabled_check and not self.enabled_check():
                        pygame.mixer.music.stop()
                        break
                    time.sleep(0.1)
            except Exception: pass

# ==================== ЗАПИСЬ АУДИО ====================
class AudioRecorder:
    def __init__(self, samplerate=16000):
        self.samplerate = samplerate
        self.frames = []
        self.stream = None
        self.recording = False

    def callback(self, indata, frames, time_info, status):
        if self.recording:
            self.frames.append(indata.copy())

    def start(self):
        self.frames = []
        self.recording = True
        self.stream = sd.InputStream(samplerate=self.samplerate, channels=1, dtype='int16', callback=self.callback)
        self.stream.start()

    def stop(self):
        self.recording = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        if not self.frames:
            return None
        data = np.concatenate(self.frames, axis=0)
        buf = io.BytesIO()
        with wave.open(buf, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.samplerate)
            wf.writeframes(data.tobytes())
        return buf.getvalue()

# ==================== ЗАПУСК ПРИЛОЖЕНИЙ ====================
def find_soffice_binary():
    std_paths = [
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"
    ]
    for p in std_paths:
        if os.path.exists(p):
            return p
    return shutil.which("soffice.exe") or "soffice.exe"

def launch_app(app_name: str) -> str:
    raw = app_name.strip().lower()
    slug = raw.replace(" ", "").replace("-", "").replace("_", "")
    soffice = find_soffice_binary()

    if any(w in slug for w in ["writer", "райтер", "ворд", "word", "документ", "текст"]):
        subprocess.Popen([soffice, "--writer"], creationflags=NO_WINDOW)
        return "LibreOffice Writer запущен."
    if any(w in slug for w in ["calc", "калк", "эксель", "excel", "таблиц"]):
        subprocess.Popen([soffice, "--calc"], creationflags=NO_WINDOW)
        return "LibreOffice Calc запущен."
    if any(w in slug for w in ["draw", "дро", "рисовани", "графика"]):
        subprocess.Popen([soffice, "--draw"], creationflags=NO_WINDOW)
        return "LibreOffice Draw запущен."
    if any(w in slug for w in ["base", "бейз", "базданных"]):
        subprocess.Popen([soffice, "--base"], creationflags=NO_WINDOW)
        return "LibreOffice Base запущен."
    if any(w in slug for w in ["libreoffice", "либреофис", "офис"]):
        subprocess.Popen([soffice], creationflags=NO_WINDOW)
        return "Стартовый центр LibreOffice запущен."

    if any(w in slug for w in ["pdf", "пдф", "читалк"]):
        for reader in ["okular.exe", "AcroRd32.exe", "SumatraPDF.exe"]:
            p = shutil.which(reader)
            if p:
                subprocess.Popen([p], creationflags=NO_WINDOW)
                return f"Просмотрщик PDF ({reader}) запущен."
        subprocess.Popen(["cmd", "/c", "start", "msedge"], shell=True, creationflags=NO_WINDOW)
        return "PDF-просмотрщик Microsoft Edge открыт."

    sites = {"youtube": "https://youtube.com", "ютуб": "https://youtube.com", "vk": "https://vk.com", "github": "https://github.com"}
    for k, url in sites.items():
        if k in slug:
            os.system(f'start "" "{url}"')
            return f"Открыт сайт {k.capitalize()}."

    win_aliases = {
        "проводник": "explorer.exe", "блокнот": "notepad.exe", "калькулятор": "calc.exe",
        "терминал": "wt.exe", "диспетчер": "taskmgr.exe", "стим": "steam.exe", "телеграм": "telegram.exe"
    }
    target = win_aliases.get(raw, raw)
    try:
        subprocess.Popen(["cmd", "/c", "start", "", target], shell=True, creationflags=NO_WINDOW)
        return f"Запущено приложение: {app_name}"
    except Exception as e:
        return f"Не удалось открыть {app_name}: {e}"

# ==================== GEMINI 3.5 FLASH ====================
class AgentWorker(QThread):
    response_ready = pyqtSignal(str)

    def __init__(self, prompt="", audio_bytes=None, screenshot_path=""):
        super().__init__()
        self.prompt = prompt
        self.audio_bytes = audio_bytes
        self.screenshot_path = screenshot_path

    def run(self):
        api_key = get_api_key()
        if not api_key:
            self.response_ready.emit("API-ключ не найден в gemini_key.txt!")
            return
        try:
            client = genai.Client(api_key=api_key)
            config = types.GenerateContentConfig(
                tools=[launch_app],
                system_instruction=(
                    "Ты голосовой системный агент Gemini под Windows 11.\n"
                    "Для запуска программ (LibreOffice, Writer, Calc, PDF, Браузер, Steam) ВСЕГДА вызывай launch_app.\n"
                    "Если пользователь просит отключить звук, замолчать или тишину — добавь: [ACTION: MUTE].\n"
                    "Если пользователь просит глубокую очистку — добавь: [ACTION: DEEP_CLEAN].\n"
                    "Если просит обычную/быструю очистку — добавь: [ACTION: CLEAN].\n"
                    "Отвечай кратко, емко, живо и по существу."
                )
            )
            chat = client.chats.create(model="gemini-3.5-flash", config=config)
            payload = []

            if self.audio_bytes:
                payload.append(types.Part.from_bytes(data=self.audio_bytes, mime_type="audio/wav"))
                payload.append("Пользователь отправил голосовое сообщение. На первой строке напиши: '🎙️ Распознано: <текст>', затем ответь и добавь маркер [ACTION], если была команда.")

            if self.screenshot_path and os.path.exists(self.screenshot_path):
                with open(self.screenshot_path, "rb") as f:
                    payload.append(types.Part.from_bytes(data=f.read(), mime_type="image/png"))

            if self.prompt:
                payload.append(self.prompt)

            resp = chat.send_message(payload)

            p_tok = getattr(resp.usage_metadata, "prompt_token_count", 0) or 0
            c_tok = getattr(resp.usage_metadata, "candidates_token_count", 0) or 0
            cost = (p_tok * 0.000000075) + (c_tok * 0.00000030)
            stats = load_stats()
            stats["total_requests"] = stats.get("total_requests", 0) + 1
            stats["prompt_tokens"] = stats.get("prompt_tokens", 0) + p_tok
            stats["candidates_tokens"] = stats.get("candidates_tokens", 0) + c_tok
            stats["cost_usd"] = stats.get("cost_usd", 0.0) + cost
            save_stats(stats)

            self.response_ready.emit(resp.text or "Готово.")
        except Exception as e:
            self.response_ready.emit(f"Ошибка Gemini: {e}")

# ==================== ГЛАВНОЕ ОКНО ====================
class AgentWindow(QWidget):
    def __init__(self, icon):
        super().__init__()
        self.setWindowIcon(icon)
        self.setWindowTitle("Gemini Windows Agent")
        self.resize(700, 560)
        self.tts_enabled = True
        self.tts_worker = None
        self.worker = None
        self.clean_worker = None
        self.recorder = AudioRecorder()
        self.is_recording = False

        layout = QVBoxLayout()
        self.hw_lbl = QLabel("Загрузка статуса...")
        self.hw_lbl.setStyleSheet("font-weight: bold; color: #00d2ff; padding: 4px; font-family: monospace;")
        layout.addWidget(self.hw_lbl)

        self.chat = QTextEdit()
        self.chat.setReadOnly(True)
        self.chat.setStyleSheet("background-color: #161822; color: #e0e6ed; font-family: monospace; font-size: 13px; border-radius: 6px;")
        layout.addWidget(self.chat)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Введите запрос или нажмите '🎙️ Сказать'...")
        self.input_field.setStyleSheet("background-color: #1f2330; color: #00ff9f; padding: 8px; font-size: 13px; border-radius: 6px;")
        self.input_field.returnPressed.connect(self.send_request)
        layout.addWidget(self.input_field)

        btn_box = QHBoxLayout()

        self.btn_send = QPushButton("Отправить")
        self.btn_send.clicked.connect(self.send_request)
        btn_box.addWidget(self.btn_send)

        self.btn_voice = QPushButton("🎙️ Сказать")
        self.btn_voice.setStyleSheet("background-color: #d97706; color: white; font-weight: bold;")
        self.btn_voice.clicked.connect(self.toggle_voice)
        btn_box.addWidget(self.btn_voice)

        self.btn_screen = QPushButton("📸 Экран")
        self.btn_screen.clicked.connect(self.analyze_screen)
        btn_box.addWidget(self.btn_screen)

        self.btn_clean = QPushButton("🧹 Быстрая")
        self.btn_clean.clicked.connect(lambda: self.start_cleaning(deep=False))
        btn_box.addWidget(self.btn_clean)

        self.btn_deep_clean = QPushButton("🧼 Глубокая")
        self.btn_deep_clean.setStyleSheet("background-color: #21262d; color: #58a6ff; border: 1px solid #30363d; font-weight: bold;")
        self.btn_deep_clean.clicked.connect(lambda: self.start_cleaning(deep=True))
        btn_box.addWidget(self.btn_deep_clean)

        self.btn_tts = QPushButton("🔊 Звук: ВКЛ")
        self.btn_tts.setStyleSheet("background-color: #065f46; color: #34d399; font-weight: bold;")
        self.btn_tts.clicked.connect(self.toggle_tts)
        btn_box.addWidget(self.btn_tts)

        layout.addLayout(btn_box)
        self.setLayout(layout)

    def stop_speech(self):
        pygame.mixer.music.stop()

    def set_tts_state(self, state: bool):
        self.tts_enabled = state
        if self.tts_enabled:
            self.btn_tts.setText("🔊 Звук: ВКЛ")
            self.btn_tts.setStyleSheet("background-color: #065f46; color: #34d399; font-weight: bold;")
        else:
            self.stop_speech()
            self.btn_tts.setText("🔇 Звук: ВЫКЛ")
            self.btn_tts.setStyleSheet("background-color: #21262d; color: #8b949e; font-weight: bold;")

    def toggle_tts(self):
        self.set_tts_state(not self.tts_enabled)

    def toggle_voice(self):
        if not self.is_recording:
            try:
                self.recorder.start()
                self.is_recording = True
                self.btn_voice.setText("🔴 Стоп")
                self.btn_voice.setStyleSheet("background-color: #dc2626; color: white; font-weight: bold;")
                self.chat.append("<i>[Слушаю микрофон... Нажмите 'Стоп' для отправки]</i><br>")
            except Exception as e:
                self.chat.append(f"<font color='red'>Ошибка микрофона: {e}</font><br>")
        else:
            self.btn_voice.setText("⏳ Обработка...")
            self.btn_voice.setStyleSheet("background-color: #4b5563; color: white;")
            self.btn_voice.setEnabled(False)
            self.is_recording = False
            wav_data = self.recorder.stop()
            if not wav_data:
                self.chat.append("<i>Запись пустая.</i><br>")
                self.btn_voice.setText("🎙️ Сказать")
                self.btn_voice.setStyleSheet("background-color: #d97706; color: white; font-weight: bold;")
                self.btn_voice.setEnabled(True)
                return

            self.chat.append("<b style='color: #00ff9f;'>Вы:</b> [🎙️ Голосовой запрос отправлен]<br>")
            self.start_worker(prompt="", audio_bytes=wav_data)

    def start_cleaning(self, deep: bool = False):
        if self.clean_worker and self.clean_worker.isRunning():
            self.chat.append("<font color='#f59e0b'>Очистка уже выполняется, подождите...</font><br>")
            return
        
        self.btn_clean.setEnabled(False)
        self.btn_deep_clean.setEnabled(False)
        btn_target = self.btn_deep_clean if deep else self.btn_clean
        btn_target.setText("⏳ Чищу...")

        self.clean_worker = CleanWorker(deep=deep)
        self.clean_worker.progress_signal.connect(lambda s: self.chat.append(f"{s}<br>"))
        self.clean_worker.finished_signal.connect(self.on_clean_finished)
        self.clean_worker.start()

    def on_clean_finished(self, summary_html):
        self.chat.append(f"{summary_html}<br>")
        self.btn_clean.setText("🧹 Быстрая")
        self.btn_deep_clean.setText("🧼 Глубокая")
        self.btn_clean.setEnabled(True)
        self.btn_deep_clean.setEnabled(True)

    def analyze_screen(self):
        self.hide()
        QTimer.singleShot(350, self._do_screen_shot)

    def _do_screen_shot(self):
        screen = QApplication.primaryScreen()
        pix = screen.grabWindow(0)
        pix.save(TEMP_SCREEN, "PNG")
        self.showNormal()
        self.activateWindow()
        self.chat.append("<b style='color: #00ff9f;'>Вы:</b> [📸 Анализ экрана]<br>")
        self.start_worker(prompt="Посмотри на экран, опиши что открыто и есть ли ошибки.", shot=TEMP_SCREEN)

    def send_request(self):
        text = self.input_field.text().strip()
        if not text:
            return
        self.input_field.clear()
        lower = text.lower()

        if any(w in lower for w in ["замолчи", "выключи звук", "отключи звук", "выключи голос", "тишина", "не говори"]):
            self.set_tts_state(False)
            self.chat.append(f"<b>Вы:</b> {text}<br><font color='#ff5252'>[Звук выключен]</font><br>")
            return

        if any(w in lower for w in ["включи звук", "включи голос", "начни говорить"]):
            self.set_tts_state(True)
            self.chat.append(f"<b>Вы:</b> {text}<br><font color='#00e676'>[Звук включен]</font><br>")
            return

        if "глубок" in lower and "очист" in lower:
            self.chat.append(f"<b>Вы:</b> {text}<br>")
            self.start_cleaning(deep=True)
            return

        if any(w in lower for w in ["почисти", "очистка", "пустые папки"]):
            self.chat.append(f"<b>Вы:</b> {text}<br>")
            self.start_cleaning(deep=False)
            return

        self.chat.append(f"<b style='color: #00ff9f;'>Вы:</b> {text}<br>")
        self.start_worker(prompt=text)

    def start_worker(self, prompt="", audio_bytes=None, shot=""):
        self.btn_send.setEnabled(False)
        self.worker = AgentWorker(prompt=prompt, audio_bytes=audio_bytes, screenshot_path=shot)
        self.worker.response_ready.connect(self.on_response)
        self.worker.start()

    def on_response(self, text):
        self.btn_send.setEnabled(True)
        self.btn_voice.setText("🎙️ Сказать")
        self.btn_voice.setStyleSheet("background-color: #d97706; color: white; font-weight: bold;")
        self.btn_voice.setEnabled(True)

        if "[ACTION: MUTE]" in text:
            text = text.replace("[ACTION: MUTE]", "").strip()
            self.set_tts_state(False)

        if "[ACTION: DEEP_CLEAN]" in text:
            text = text.replace("[ACTION: DEEP_CLEAN]", "").strip()
            self.start_cleaning(deep=True)

        if "[ACTION: CLEAN]" in text:
            text = text.replace("[ACTION: CLEAN]", "").strip()
            self.start_cleaning(deep=False)

        self.chat.append(f"<b style='color: #bd00ff;'>Светлана:</b> {text}<br>")
        if self.tts_enabled:
            self.tts_worker = TTSWorker(text, enabled_check=lambda: self.tts_enabled)
            self.tts_worker.start()

def ensure_autostart():
    try:
        if sys.platform == "win32":
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
            cmd = f'"{sys.executable}"' if getattr(sys, 'frozen', False) else f'"{sys.executable}" "{os.path.abspath(__file__)}"'
            winreg.SetValueEx(key, "GeminiAgent", 0, winreg.REG_SZ, cmd)
            winreg.CloseKey(key)
        else:
            autostart_dir = os.path.expanduser("~/.config/autostart")
            os.makedirs(autostart_dir, exist_ok=True)
            desktop_path = os.path.join(autostart_dir, "gemini-agent.desktop")
            if not os.path.exists(desktop_path):
                exec_cmd = sys.executable if getattr(sys, 'frozen', False) else f"{sys.executable} {os.path.abspath(__file__)}"
                content = f"[Desktop Entry]\nType=Application\nName=Gemini Agent\nExec={exec_cmd}\nTerminal=false\n"
                with open(desktop_path, "w", encoding="utf-8") as df:
                    df.write(content)
    except Exception:
        pass

def main():
    ensure_autostart()
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    icon = ensure_gemini_icon()
    window = AgentWindow(icon)

    tray = QSystemTrayIcon(icon, app)
    menu = QMenu()

    act_cpu = QAction("⚡ CPU: ...", menu)
    act_cpu.setEnabled(False)
    act_ram = QAction("🧠 RAM: ...", menu)
    act_ram.setEnabled(False)
    act_vram = QAction("🎮 VRAM: ...", menu)
    act_vram.setEnabled(False)
    act_bal = QAction("💳 Расход: ...", menu)
    act_bal.setEnabled(False)

    menu.addAction(act_cpu)
    menu.addAction(act_ram)
    menu.addAction(act_vram)
    menu.addAction(act_bal)
    menu.addSeparator()

    menu.addAction("💬 Открыть окно").triggered.connect(window.showNormal)
    menu.addAction("🎙️ Голосовой ввод").triggered.connect(lambda: (window.showNormal(), window.toggle_voice()))
    menu.addAction("🧹 Быстрая очистка").triggered.connect(lambda: window.start_cleaning(deep=False))
    menu.addAction("🧼 Глубокая очистка (DISM, апдейты)").triggered.connect(lambda: window.start_cleaning(deep=True))
    menu.addAction("📸 Снимок экрана").triggered.connect(window.analyze_screen)
    menu.addSeparator()
    menu.addAction("❌ Завершить").triggered.connect(app.quit)

    tray.setContextMenu(menu)
    tray.activated.connect(lambda r: window.showNormal() if r == QSystemTrayIcon.ActivationReason.Trigger else None)
    tray.show()

    def update_hardware():
        m = get_system_metrics()
        tooltip_text = f"Gemini Agent\n⚡ CPU: {m['cpu']} | 🧠 RAM: {m['ram']}\n🎮 {m['vram']} | 💳 {m['balance']}"
        tray.setToolTip(tooltip_text)

        act_cpu.setText(f"⚡ CPU: {m['cpu']}")
        act_ram.setText(f"🧠 RAM: {m['ram']}")
        act_vram.setText(f"🎮 {m['vram']}")
        act_bal.setText(f"💳 Затраты: {m['balance']} (Запросов: {m['requests']})")

        window.hw_lbl.setText(f"⚡ CPU: {m['cpu']}  │  🧠 RAM: {m['ram']}  │  🎮 {m['vram']}  │  💳 {m['balance']}")

    update_hardware()
    hw_timer = QTimer()
    hw_timer.timeout.connect(update_hardware)
    hw_timer.start(2500)

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
