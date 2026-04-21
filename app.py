import os
import subprocess
import pty
import select
import shutil
import signal
import stat
import zipfile
import tarfile
import json
import time
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
from threading import Thread, Lock
from werkzeug.utils import secure_filename

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

app = Flask(__name__, template_folder='.')
app.config['SECRET_KEY'] = 'nexus_secret_key_v4'
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

# --- MULTI-SESSION SHELL MANAGER ---
sessions = {}       # sid -> { master_fd, shell_process, thread }
session_lock = Lock()

def start_shell_for_session(sid):
    """Spawn a fresh PTY shell for a given socket session ID."""
    master_fd, slave_fd = pty.openpty()

    shell_cmd = os.environ.get('SHELL', '/bin/bash')
    if os.path.exists('/data/data/com.termux/files/usr/bin/bash'):
        shell_cmd = '/data/data/com.termux/files/usr/bin/bash'

    env = os.environ.copy()
    env["TERM"] = "xterm-256color"

    proc = subprocess.Popen(
        [shell_cmd], stdin=slave_fd, stdout=slave_fd, stderr=slave_fd,
        preexec_fn=os.setsid, close_fds=True, env=env
    )
    os.close(slave_fd)

    # Greeting
    os.write(master_fd, b"clear\n")
    os.write(master_fd, b"echo -e '\\e[1;32mWelcome. NEXUS CONTROL V4 initialized.\\e[0m'\n")
    os.write(master_fd, b"echo -e '\\e[1;30mstay legal. stay anonymous.\\e[0m'\n\n")

    def reader():
        while True:
            try:
                r, _, _ = select.select([master_fd], [], [], 0.1)
                if master_fd in r:
                    out = os.read(master_fd, 10240).decode(errors='replace')
                    if out:
                        socketio.emit('term_output', {'data': out, 'sid': sid}, room=sid)
            except OSError:
                break

    t = Thread(target=reader, daemon=True)
    t.start()

    with session_lock:
        sessions[sid] = {'master_fd': master_fd, 'process': proc, 'thread': t}

    return master_fd


def kill_session(sid):
    with session_lock:
        info = sessions.pop(sid, None)
    if info:
        try:
            os.kill(info['process'].pid, signal.SIGKILL)
        except Exception:
            pass
        try:
            os.close(info['master_fd'])
        except Exception:
            pass


@socketio.on('connect')
def on_connect():
    sid = request.sid
    start_shell_for_session(sid)
    emit('session_ready', {'sid': sid})


@socketio.on('disconnect')
def on_disconnect():
    kill_session(request.sid)


@socketio.on('new_session')
def handle_new_session():
    """Client requests a brand-new shell (for Arsenal tool isolation)."""
    sid = request.sid
    kill_session(sid)
    start_shell_for_session(sid)
    emit('session_ready', {'sid': sid})


@socketio.on('run_command')
def handle_command(json_data):
    sid = request.sid
    cmd = json_data.get('command', '')
    is_raw = json_data.get('is_raw', False)
    payload = cmd.encode('utf-8') if is_raw else (cmd + '\n').encode('utf-8')

    with session_lock:
        info = sessions.get(sid)

    if info:
        try:
            os.write(info['master_fd'], payload)
        except OSError:
            start_shell_for_session(sid)
            with session_lock:
                info = sessions.get(sid)
            if info:
                os.write(info['master_fd'], payload)


# --- ROUTES ---
@app.route('/')
def index():
    return render_template('dashboard.html', tools=MY_TOOLS)


# --- SYSTEM STATS API ---
@app.route('/api/stats')
def get_stats():
    if not PSUTIL_AVAILABLE:
        return jsonify({"error": "psutil not installed. Run: pip install psutil"})
    try:
        cpu = psutil.cpu_percent(interval=0.2)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        net = psutil.net_io_counters()
        return jsonify({
            "cpu_percent": cpu,
            "ram_percent": ram.percent,
            "ram_used_mb": round(ram.used / 1024 / 1024, 1),
            "ram_total_mb": round(ram.total / 1024 / 1024, 1),
            "disk_percent": disk.percent,
            "disk_used_gb": round(disk.used / 1024 / 1024 / 1024, 2),
            "disk_total_gb": round(disk.total / 1024 / 1024 / 1024, 2),
            "net_sent_mb": round(net.bytes_sent / 1024 / 1024, 2),
            "net_recv_mb": round(net.bytes_recv / 1024 / 1024, 2),
            "timestamp": time.time()
        })
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route('/api/processes')
def get_processes():
    if not PSUTIL_AVAILABLE:
        return jsonify([{"pid": "ERR", "name": "psutil missing. Run: pip install psutil", "memory_percent": 0, "cpu_percent": 0, "status": "unknown", "username": ""}])
    procs = []
    for proc in psutil.process_iter(['pid', 'name', 'memory_percent', 'cpu_percent', 'status', 'username', 'num_threads']):
        try:
            procs.append(proc.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    procs.sort(key=lambda x: x.get('cpu_percent') or 0, reverse=True)
    return jsonify(procs[:30])


@app.route('/api/kill', methods=['POST'])
def kill_process():
    if not PSUTIL_AVAILABLE:
        return jsonify({"status": "error", "message": "psutil not installed"})
    try:
        os.kill(int(request.json.get('pid')), signal.SIGKILL)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


# --- FILE MANAGER APIS ---
def octal_to_symbolic(mode):
    """Convert stat mode to rwxrwxrwx string."""
    perms = ''
    for who in [(stat.S_IRUSR, stat.S_IWUSR, stat.S_IXUSR),
                (stat.S_IRGRP, stat.S_IWGRP, stat.S_IXGRP),
                (stat.S_IROTH, stat.S_IWOTH, stat.S_IXOTH)]:
        perms += 'r' if mode & who[0] else '-'
        perms += 'w' if mode & who[1] else '-'
        perms += 'x' if mode & who[2] else '-'
    return perms


@app.route('/api/files', methods=['POST'])
def list_files():
    try:
        abs_path = os.path.abspath(request.json.get('path', '.'))
        items = []
        for e in os.scandir(abs_path):
            try:
                s = e.stat()
                items.append({
                    "name": e.name,
                    "is_dir": e.is_dir(),
                    "path": e.path,
                    "size": s.st_size,
                    "permissions": octal_to_symbolic(s.st_mode),
                    "octal": oct(stat.S_IMODE(s.st_mode)),
                    "modified": s.st_mtime
                })
            except Exception:
                items.append({"name": e.name, "is_dir": e.is_dir(), "path": e.path, "size": 0, "permissions": "?????????", "octal": "0o000", "modified": 0})
        items.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
        return jsonify({"status": "success", "current_path": abs_path, "items": items})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


@app.route('/api/file-search', methods=['POST'])
def file_search():
    try:
        data = request.json
        base = os.path.abspath(data.get('path', '.'))
        query = data.get('query', '').lower()
        results = []
        for root, dirs, files in os.walk(base):
            for name in dirs + files:
                if query in name.lower():
                    full = os.path.join(root, name)
                    try:
                        s = os.stat(full)
                        results.append({
                            "name": name,
                            "path": full,
                            "is_dir": os.path.isdir(full),
                            "size": s.st_size,
                            "permissions": octal_to_symbolic(s.st_mode),
                            "octal": oct(stat.S_IMODE(s.st_mode)),
                            "modified": s.st_mtime
                        })
                    except Exception:
                        pass
            if len(results) >= 100:
                break
        return jsonify({"status": "success", "results": results[:100]})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


@app.route('/api/chmod', methods=['POST'])
def change_permissions():
    data = request.json
    path = data.get('path')
    mode_str = data.get('mode', '')
    try:
        mode = int(mode_str, 8)
        os.chmod(path, mode)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file part"})
    file = request.files['file']
    if file.filename == '':
        return jsonify({"status": "error", "message": "No selected file"})
    try:
        dest = os.path.join(request.form.get('path', app.config['UPLOAD_FOLDER']), secure_filename(file.filename))
        file.save(dest)
        return jsonify({"status": "success", "message": f"Uploaded {secure_filename(file.filename)}"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


@app.route('/api/file-op', methods=['POST'])
def file_operations():
    data = request.json
    action = data.get('action')
    path = data.get('path')
    try:
        if action == 'read':
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                return jsonify({"status": "success", "content": f.read()})
        elif action == 'save':
            with open(path, 'w', encoding='utf-8') as f:
                f.write(data.get('content', ''))
            return jsonify({"status": "success"})
        elif action == 'create_folder':
            os.makedirs(path, exist_ok=True)
        elif action == 'create_file':
            open(path, 'w').close()
        elif action == 'delete':
            shutil.rmtree(path) if os.path.isdir(path) else os.remove(path)
        elif action == 'rename':
            os.rename(path, data.get('new_path'))
        elif action == 'zip':
            zip_path = path + '.zip'
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                if os.path.isdir(path):
                    for root, dirs, files in os.walk(path):
                        for file in files:
                            full = os.path.join(root, file)
                            zf.write(full, os.path.relpath(full, os.path.dirname(path)))
                else:
                    zf.write(path, os.path.basename(path))
            return jsonify({"status": "success", "zip_path": zip_path})
        elif action == 'unzip':
            dest = data.get('dest', os.path.dirname(path))
            if path.endswith('.zip'):
                with zipfile.ZipFile(path, 'r') as zf:
                    zf.extractall(dest)
            elif path.endswith(('.tar.gz', '.tgz', '.tar.bz2', '.tar')):
                with tarfile.open(path, 'r:*') as tf:
                    tf.extractall(dest)
            else:
                return jsonify({"status": "error", "message": "Unsupported archive format"})
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
