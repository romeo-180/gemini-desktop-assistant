# 🤖 Gemini Desktop System Agent (Windows & Linux)

🌐 **Language / Язык:** [**🇺🇸 English**](README.md) | [**🇷🇺 Русский**](README.ru.md)

Smart voice & system AI assistant powered by **Google Gemini** living in your system tray. It automatically finds and launches **any installed application or game** on your PC, cleans up system junk and RAM, analyzes your screen, and speaks in a natural voice (auto-switching between English and Russian).

---

## 🚀 Quick Installation

### 🪟 Windows 10 / 11
**Option 1 — Standalone Executable (Easiest):**
1. Download **`GeminiAgent-Windows.exe`** from **[Releases](https://github.com/romeo-180/gemini-windows-agent/releases/latest)**.
2. Double-click to run. On first launch, choose your language (**English / Русский**), and the app will configure autostart and prompt for your free Gemini API key.

**Option 2 — 1-Line PowerShell Installer:**
```powershell
irm https://raw.githubusercontent.com/romeo-180/gemini-desktop-assistant/main/install.ps1 | iex
```

---

### 🐧 Linux (Arch Linux, Ubuntu, Debian, Fedora)
Open your terminal and run this single command:
```bash
curl -sSL https://raw.githubusercontent.com/romeo-180/gemini-desktop-assistant/main/install.sh | bash
```
The installer automatically detects your distro (`pacman`, `apt`, or `dnf`), installs required packages, creates an app menu shortcut, enables autostart, and prompts for your language and API key.

*(Or download the portable **`GeminiAgent-Linux`** binary from **[Releases](https://github.com/romeo-180/gemini-windows-agent/releases/latest)**).*

---

## 🔑 How to Get a Free Gemini API Key
On first launch, click **«🔑 Get Free API Key»** in the prompt window, or get one in 1 minute:
1. Open **[Google AI Studio](https://aistudio.google.com/)** and sign in with your Google account.
2. Click **«Create API key»** (or **«Get API key»**) and copy the key (`AIzaSy...`).
3. Paste it into the prompt window when the app starts.

---

## ✨ What the Assistant Can Do

* **🚀 Launch ANY Installed App, Game, or Website:**
  The agent automatically scans all shortcuts and applications installed on your PC (Start Menu, Desktop, Steam, and Linux `.desktop` launchers). Just say or type: *"Open Blender"*, *"Launch Telegram"*, *"Start Cyberpunk"*, *"Open browser"*, or *"Open YouTube"* — in any language.
* **🎙 Voice & Text Interaction (`🎙 Speak` button):**
  Understand and replies in **any language**, automatically selecting a natural voice (Aria for English, Svetlana for Russian).
* **🔇 Instant Voice Control:**
  Say *"Mute"* / *"Stop speaking"* to switch to silent text-only mode, or *"Unmute"* to bring the voice back.
* **🧹 Fast System Cleanup (`🧹 Fast Clean` button or *"Clean up"* command):**
  Clears temporary files (`Temp`), shader/thumbnail caches, empties the Recycle Bin / Trash, and frees up unused RAM.
* **🔥 Deep System Cleanup (`🔥 Deep Clean` button or *"Deep clean"* command):**
  Removes crash dumps, cleans package/update caches (`WinSxS` on Windows / `paccache` & `journalctl` on Linux), and compacts system storage.
* **👁 Screen Vision (`👁 Screen` button):**
  Takes a snapshot of your screen and uses Gemini Vision to analyze open windows, read errors, or help with whatever you are looking at.
* **📊 Live System Tray Monitoring:**
  * **Hover over the tray icon:** Shows live CPU, RAM, VRAM load, and API token balance.
  * **Right-click the tray icon:** Opens quick actions and real-time system metrics.
