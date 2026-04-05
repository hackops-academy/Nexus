import os
import subprocess
import pty
import select
import shutil
import signal
import sys
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
from threading import Thread
from werkzeug.utils import secure_filename

# Optional import for process management
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

# Set template_folder='.' so it finds dashboard.html in the same directory
app = Flask(__name__, template_folder='.')
app.config['SECRET_KEY'] = 'nexus_secret_key'
app.config['UPLOAD_FOLDER'] = os.getcwd()

socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# --- ARSENAL INTEL ---
MY_TOOLS = [
    {
        "name": "copycat-CLI", 
        "url": "https://github.com/hackops-academy/copycat-CLI", 
        "run_cmd": "cd ~/copycat-CLI && chmod +x copycat-CLI.sh && ./copycat-CLI.sh",
        "manual": "A sophisticated CLI utility for rapid repository cloning, environment setup, and asset duplication.",
        "use_cases": ["Automated environment cloning", "Red team asset deployment", "Rapid script execution"]
    },
    {
        "name": "AstralOSINT", 
        "url": "https://github.com/hackops-academy/AstralOSINT", 
        "run_cmd": "cd ~/AstralOSINT && chmod +x run.sh && ./run.sh",
        "manual": "A powerful geospatial intelligence and OSINT console. Features coordinate extraction and route mapping.",
        "use_cases": ["Geospatial mapping", "Target location correlation", "Route analysis"]
    },
    {
        "name": "MetaGhost v3.0", 
        "url": "https://github.com/hackops-academy/MetaGhost", 
        "run_cmd": "cd ~/MetaGhost && chmod +x MetaGhost.sh && ./MetaGhost.sh",
        "manual": "Advanced metadata extraction and forensic removal tool for payload sanitization and OpSec.",
        "use_cases": ["Pre-deployment payload sanitization", "OpSec verification", "Forensic analysis evasion"]
    },
    {
        "name": "CrackSmith", 
        "url": "https://github.com/hackops-academy/CrackSmith", 
        "run_cmd": "cd ~/CrackSmith && chmod +x CrackSmith.sh && ./CrackSmith.sh",
        "manual": "Offensive security utility for generating custom wordlists and bruteforcing basic hashes.",
        "use_cases": ["Hash cracking", "Custom dictionary generation", "Cryptographic vulnerability research"]
    },
    {
        "name": "Ghost-CLI", 
        "url": "https://github.com/hackops-academy/Ghost-CLI", 
        "run_cmd": "cd ~/Ghost-CLI && chmod +x ghost.sh && ./ghost.sh",
        "manual": "Anonymization routing script for Linux and Termux. Manipulates proxy settings and routing.",
        "use_cases": ["Traffic obfuscation", "IP masking", "Secure terminal proxying"]
    }
]

# --- PERSISTENT SHELL SETUP ---
master_fd = None
shell_process = None

def start_shell():
    global master_fd, shell_process
    
    if shell_process and shell_process.poll() is None:
        shell_process.terminate()

    master_fd, slave_fd = pty.openpty()
    
    # Auto-detect Termux or fallback to standard Linux shell
    shell_cmd = os.environ.get('SHELL', '/bin/bash')
    if os.path.exists('/data/data/com.termux/files/usr/bin/bash'):
        shell_cmd = '/data/data/com.termux/files/usr/bin/bash' 
        
    env = os.environ.copy()
    env["TERM"] = "xterm-256color"

    shell_process = subprocess.Popen(
        [shell_cmd], stdin=slave_fd, stdout=slave_fd, stderr=slave_fd,
        preexec_fn=os.setsid, close_fds=True, env=env
    )
    os.close(slave_fd)
    
    # Inject Custom Greeting Sequence
    os.write(master_fd, b"clear\n")
    os.write(master_fd, b"echo -e '\\e[1;32mWelcome Lekhraj. Hackops Academy Nexus Control initialized.\\e[0m'\n")
    os.write(master_fd, b"echo -e '\\e[1;30mstay legal. stay anonymous.\\e[0m'\n\n")

    Thread(target=read_from_shell, daemon=True).start()

def read_from_shell():
    global master_fd
    while True:
        try:
            r, _, _ = select.select([master_fd], [], [], 0.1)
            if master_fd in r:
                output = os.read(master_fd, 10240).decode(errors='replace')
                if output: 
                    socketio.emit('term_output', {'data': output})
        except (OSError, Exception):
            break

if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
    start_shell()

# --- ROUTES ---
@app.route('/')
def index():
    return render_template('dashboard.html', tools=MY_TOOLS)

@app.route('/api/processes')
def get_processes():
    if not PSUTIL_AVAILABLE:
        return jsonify([{"pid": "ERR", "name": "psutil missing. Run: pip install psutil", "memory_percent": 0.0}])
    procs = []
    for proc in psutil.process_iter(['pid', 'name', 'memory_percent']):
        try: procs.append(proc.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied): pass
    procs.sort(key=lambda x: x['memory_percent'] or 0, reverse=True)
    return jsonify(procs[:20])

@app.route('/api/kill', methods=['POST'])
def kill_process():
    if not PSUTIL_AVAILABLE: return jsonify({"status": "error", "message": "psutil not installed"})
    try:
        os.kill(int(request.json.get('pid')), signal.SIGKILL)
        return jsonify({"status": "success"})
    except Exception as e: return jsonify({"status": "error", "message": str(e)})

@app.route('/api/files', methods=['POST'])
def list_files():
    try:
        abs_path = os.path.abspath(request.json.get('path', '.'))
        items = [{"name": e.name, "is_dir": e.is_dir(), "path": e.path, "size": e.stat().st_size} for e in os.scandir(abs_path)]
        items.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
        return jsonify({"status": "success", "current_path": abs_path, "items": items})
    except Exception as e: return jsonify({"status": "error", "message": str(e)})

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files: return jsonify({"status": "error", "message": "No file part"})
    file = request.files['file']
    if file.filename == '': return jsonify({"status": "error", "message": "No selected file"})
    try:
        file.save(os.path.join(request.form.get('path', app.config['UPLOAD_FOLDER']), secure_filename(file.filename)))
        return jsonify({"status": "success", "message": f"Uploaded {secure_filename(file.filename)}"})
    except Exception as e: return jsonify({"status": "error", "message": str(e)})

@app.route('/api/file-op', methods=['POST'])
def file_operations():
    data = request.json
    action, path = data.get('action'), data.get('path')
    try:
        if action == 'read':
            with open(path, 'r', encoding='utf-8', errors='replace') as f: return jsonify({"status": "success", "content": f.read()})
        elif action == 'save':
            with open(path, 'w', encoding='utf-8') as f: f.write(data.get('content'))
            return jsonify({"status": "success"})
        elif action == 'create_folder': os.makedirs(path, exist_ok=True)
        elif action == 'create_file': open(path, 'w').close()
        elif action == 'delete': shutil.rmtree(path) if os.path.isdir(path) else os.remove(path)
        return jsonify({"status": "success"})
    except Exception as e: return jsonify({"status": "error", "message": str(e)})

@socketio.on('run_command')
def handle_command(json_data):
    global master_fd
    cmd = json_data.get('command', '')
    payload = cmd.encode('utf-8') if json_data.get('is_raw') else (cmd + '\n').encode('utf-8')
    try: os.write(master_fd, payload)
    except OSError:
        start_shell()
        os.write(master_fd, payload)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
