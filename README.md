
# 🕸️ NEXUS Control Console

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-blue.svg" alt="Python Version">
  <img src="https://img.shields.io/badge/Framework-Flask-lightgrey.svg" alt="Flask">
  <img src="https://img.shields.io/badge/Environment-Termux%20%7C%20Linux-success.svg" alt="Environment">
  <img src="https://img.shields.io/badge/Status-Active-brightgreen.svg" alt="Status">
</p>

## 📌 Overview
**NEXUS** is an advanced, lightweight web-based management interface engineered specifically for Termux and Linux environments. Built with a Python/Flask backend and a dynamic xterm.js frontend, it provides penetration testers, security researchers, and developers with a centralized dashboard to command their local environment from any web browser.

Whether you are managing complex file structures, monitoring system processes, or deploying offensive security assets, NEXUS acts as your unified operational headquarters.

---

## ⚡ Key Features

* **💻 Persistent Web Shell:** A high-fidelity, persistent terminal session powered by `pty` and `xterm.js`. Features dynamic resizing, custom font scaling, and a dedicated mobile-friendly `CTRL` interface for complex keybindings.
* **☠️ The Arsenal:** A tactical deployment tab pre-configured to clone and launch offensive security and OSINT utilities directly into your workspace. Complete with built-in operator manuals and use-case briefs.
* **📂 Advanced File Manager:** Navigate your filesystem seamlessly. Supports file uploads, directory creation, deletion, and includes a built-in full-screen code editor for modifying scripts on the fly.
* **⚙️ Process Manager:** Monitor active system tasks, view memory consumption, and terminate rogue processes with a single click. *(Features graceful degradation if `psutil` is unsupported on the host device).*
* **📱 Mobile Optimized:** A responsive, dark-themed UI built with Bootstrap 5, designed specifically to prevent native scrolling conflicts during active terminal sessions on mobile devices.

---

## 🛠️ Tech Stack

* **Backend:** Python 3, Flask, Flask-SocketIO, `pty`, `psutil`
* **Frontend:** HTML5, CSS3, JavaScript, Bootstrap 5, xterm.js
* **Integration:** Bash, Git, Termux API (optional)

---

## 🚀 Installation & Setup

NEXUS is heavily optimized for **Termux** on Android but works exceptionally well on standard Linux distributions (like Kali Linux).

### 1. Prerequisites
Ensure your system is up to date and has Python and Git installed.
```bash
pkg update && pkg upgrade -y
pkg install python git clang -y
```

### 2. Clone the Repository
```bash
git clone https://github.com/hackops-academy/Nexus
cd Nexus
chmod +x app.py
```

### 3. Install Dependencies
Install the required Python modules. (Note: psutil is optional but highly recommended for the Task Manager feature to function fully).
```bash
pip install flask flask-socketio werkzeug
pkg install python-psutil -y  # Termux specific optimized install
```
### 4. Launch the Console
```bash
python3 app.py
```

The console will bind to 127.0.0.1:5000 by default. Open your browser and navigate to http://localhost:5000 or your device's local IP address to access the dashboard.
🗡️ The Arsenal Integration
NEXUS comes pre-configured to deploy elite tools from the Hackops Academy ecosystem directly to your home directory (~/):
 * copycat-CLI: Rapid repository cloning and environment setup.
 * AstralOSINT: Geospatial intelligence and OSINT mapping console.
 * MetaGhost (v3.0): Advanced metadata extraction and forensic removal.
 * CrackSmith: Custom wordlist generation and cryptographic vulnerability research.
 * DomainHunter: Subdomain enumeration and attack surface mapping.
 * Ghost-CLI: Anonymization routing and traffic obfuscation.
To add your own tools, simply edit the MY_TOOLS dictionary located at the top of app.py.


## ⚠️ Disclaimer & Ethics
This tool is developed for educational purposes, authorized penetration testing, and security research. The developer and Hackops Academy assume no liability and are not responsible for any misuse or damage caused by this program.
Ensure you have explicit permission before deploying offensive modules against any target or network.
> stay legal. stay anonymous.


## 👨‍💻 Author
Developed by Lekhraj Singh Lead Developer & Founder at Hackops Academy
<p align="center">
<i>"Empowering elite operators through advanced security research."</i>
</p>
