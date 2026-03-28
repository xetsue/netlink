import os
import socket
import http.server
import socketserver
import urllib.parse
import sys
import argparse
import shutil
import tempfile
import json
import datetime

target_path = ""
target_type = ""
accent_color = "#ffe8a8"
RED = "\033[91m"
RESET = "\033[0m"
ASCII_ART = r"""
  __  __     ______     __  __    
/\_\_\_\   /  ___\   /\ \/\ \   
\/_/\_\/_  \ \___  \  \ \ \_\ \  
  /\_\/\_\  \/\_____\  \ \_____\ 
  \/_/\/_/   \/_____/   \/_____/
  
  [   Netlink — Necessary Speed   ] 
"""

class GlassHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed_url.query)
        path = self.translate_path(parsed_url.path)

        if 'zip' in query:
            folder_name = query['zip'][0]
            folder_path = os.path.join(path, folder_name)
            if os.path.isdir(folder_path):
                temp_dir = tempfile.mkdtemp()
                zip_base = os.path.join(temp_dir, os.path.basename(os.path.normpath(folder_path)))
                shutil.make_archive(zip_base, 'zip', folder_path)
                zip_filepath = zip_base + '.zip'
                self.stream_file(zip_filepath, cleanup_dir=temp_dir)
                return

        if 'deepscan' in query:
            term = query['deepscan'][0].lower()
            results = []
            count = 0
            try:
                for root, dirs, files in os.walk(path):
                    for name in files:
                        if term in name.lower():
                            full_path = os.path.join(root, name)
                            rel_path = os.path.relpath(full_path, path)
                            try:
                                stat = os.stat(full_path)
                                size, mtime = stat.st_size, stat.st_mtime
                            except Exception:
                                size, mtime = 0, 0
                            results.append({"name": rel_path.replace('\\', '/'), "size": size, "date": mtime})
                            count += 1
                            if count >= 1000:
                                break
                    if count >= 1000:
                        break
            except Exception:
                pass

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(results).encode('utf-8'))
            return

        if os.path.isdir(path):
            self.list_directory(path)
        elif os.path.isfile(path):
            self.stream_file(path)
        else:
            self.send_error(404, "File Not Found")

    def translate_path(self, path):
        if target_type == "file":
            if path == "/":
                return os.path.dirname(target_path)
            elif path == "/" + urllib.parse.quote(os.path.basename(target_path)):
                return target_path
            else:
                return ""
        
        path = urllib.parse.unquote(path).split('?', 1)[0].split('#', 1)[0]
        path = os.path.normpath(path).lstrip('/')
        return os.path.abspath(os.path.join(os.getcwd(), path))

    def stream_file(self, path, cleanup_dir=None):
        try:
            file_size = os.path.getsize(path)
            with open(path, 'rb') as f:
                self.send_response(200)
                self.send_header("Content-type", "application/octet-stream")
                self.send_header("Content-Disposition", f'attachment; filename="{os.path.basename(path)}"')
                self.send_header("Content-Length", str(file_size))
                self.end_headers()
                
                while True:
                    chunk = f.read(65536)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
        except (OSError, PermissionError):
            self.send_error(403, "System Access Denied")
        except Exception:
            pass
        finally:
            if cleanup_dir and os.path.exists(cleanup_dir):
                shutil.rmtree(cleanup_dir, ignore_errors=True)

    def list_directory(self, path):
        displaypath = urllib.parse.unquote(urllib.parse.urlparse(self.path).path)
        
        html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Netlink by XSU.</title>
<style>
:root {{
    --accent-color: {accent_color};
    --font-size: 16px;
}}
body {{ background-color: #050505; color: #f0f0f0; font-family: monospace; margin: 0; padding: 40px; display: flex; justify-content: center; min-height: 100vh; font-size: var(--font-size); overflow-x: hidden; }}
#ascii-anim {{ position: fixed; top: 20px; left: 40px; font-size: 1.5em; color: var(--accent-color); z-index: 1000; font-weight: bold; text-shadow: 0 0 10px rgba(255,255,255,0.2); }}
.top-bar {{ position: fixed; top: 20px; right: 40px; z-index: 1000; }}
.settings-btn {{ background: rgba(255,255,255,0.05); border: 1px solid var(--accent-color); color: #fff; padding: 10px 15px; border-radius: 8px; cursor: pointer; font-size: 1.5em; backdrop-filter: blur(10px); display: flex; align-items: center; justify-content: center; width: 50px; height: 50px; transition: all 0.3s ease; }}
.settings-btn:hover {{ background: rgba(255,255,255,0.1); transform: scale(1.05); }}
.settings-panel {{ display: none; position: absolute; top: 60px; right: 0; width: 280px; background: rgba(10,10,10,0.8); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 25px; box-shadow: 0 10px 40px rgba(0,0,0,0.7); flex-direction: column; gap: 20px; }}
.settings-panel.active {{ display: flex; }}
.setting-item {{ display: flex; justify-content: space-between; align-items: center; color: #ccc; font-size: 0.9em; }}
.setting-item span {{ flex-shrink: 0; }}
.setting-item input[type="color"] {{ background: none; border: 1px solid rgba(255,255,255,0.2); border-radius: 4px; cursor: pointer; height: 35px; width: 50px; padding: 0; }}
.setting-item input[type="range"] {{ flex-grow: 1; margin-left: 15px; accent-color: var(--accent-color); }}
.setting-item input[type="checkbox"] {{ width: 20px; height: 20px; cursor: pointer; accent-color: var(--accent-color); }}
.glass-container {{ background: rgba(255, 255, 255, 0.03); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 16px; padding: 40px; width: 100%; max-width: 1400px; box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5); display: flex; flex-direction: column; margin-top: 40px; }}
.brand-header {{ font-size: 1.5em; color: #ffffff; text-align: center; margin-bottom: 30px; letter-spacing: 2px; border-bottom: 2px solid var(--accent-color); padding-bottom: 20px; font-weight: bold; opacity: 0.9; }}
h1 {{ border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 20px; margin-top: 0; font-size: 1.1em; letter-spacing: 1px; color: #aaa; }}
.controls {{ display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; }}
.controls input, .controls select {{ background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.2); color: #fff; padding: 12px; border-radius: 8px; font-family: monospace; font-size: 1em; outline: none; transition: border-color 0.3s ease; }}
.controls input {{ flex-grow: 1; }}
.controls input:focus, .controls select:focus {{ background: rgba(255,255,255,0.1); border-color: var(--accent-color); }}
.controls select option {{ background: #111; color: #fff; }}
ul {{ list-style-type: none; padding: 0; margin: 0; }}
li {{ display: flex; gap: 10px; margin: 15px 0; align-items: stretch; }}
li.section-header {{ color: var(--accent-color); font-size: 1.2em; font-weight: bold; border-bottom: 1px dashed rgba(255,255,255,0.2); padding-bottom: 5px; margin-top: 30px; text-transform: uppercase; letter-spacing: 1px; }}
a {{ text-decoration: none; border-radius: 8px; border: 1px solid transparent; transition: all 0.3s ease; background: rgba(255,255,255,0.02); word-wrap: break-word; }}
.main-link {{ flex-grow: 1; color: var(--accent-color); display: flex; justify-content: space-between; padding: 20px; }}
.main-link:hover {{ background: rgba(255,255,255,0.08); color: #fff; border-color: rgba(255,255,255,0.2); transform: translateX(8px); }}
.dl-btn {{ color: var(--accent-color); display: flex; align-items: center; justify-content: center; padding: 0 25px; font-size: 1.4em; }}
.dl-btn:hover {{ background: rgba(255,255,255,0.08); color: #fff; border-color: rgba(255,255,255,0.2); transform: scale(1.05); }}
.meta-info {{ color: #888; font-size: 0.85em; text-align: right; }}
.modal {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); z-index: 2000; align-items: center; justify-content: center; backdrop-filter: blur(8px); }}
.modal.active {{ display: flex; }}
.modal-content {{ background: rgba(15,15,15,0.95); border: 1px solid var(--accent-color); padding: 40px; border-radius: 12px; text-align: center; box-shadow: 0 10px 50px rgba(0,0,0,0.8); max-width: 400px; }}
.modal-content p {{ font-size: 1.2em; margin-bottom: 30px; color: #fff; }}
.modal-btns {{ display: flex; gap: 20px; justify-content: center; }}
.modal-btns button {{ background: rgba(255,255,255,0.05); color: #fff; border: 1px solid var(--accent-color); padding: 12px 30px; border-radius: 8px; cursor: pointer; font-family: monospace; font-size: 1em; transition: 0.3s; }}
.modal-btns button:hover {{ background: var(--accent-color); color: #000; font-weight: bold; }}
</style>
</head>
<body>
<div id="ascii-anim">(=.=)</div>
<div class="top-bar">
    <button class="settings-btn" id="settingsBtn">⋰</button>
    <div class="settings-panel" id="settingsPanel">
        <div class="setting-item">
            <span>Accent Color</span>
            <input type="color" id="colorPicker" value="{accent_color}">
        </div>
        <div class="setting-item">
            <span>Font Size</span>
            <input type="range" id="fontSizeSlider" min="10" max="30" value="16">
        </div>
        <div class="setting-item">
            <span>Deepscan Search</span>
            <input type="checkbox" id="deepScanCheck">
        </div>
        <div class="setting-item">
            <span>Section by Type</span>
            <input type="checkbox" id="sectionTypeCheck">
        </div>
        <div class="setting-item">
            <span>Confirm Folder ZIP</span>
            <input type="checkbox" id="confFolderCheck" checked>
        </div>
        <div class="setting-item">
            <span>Confirm File DL</span>
            <input type="checkbox" id="confFileCheck">
        </div>
    </div>
</div>

<div class="modal" id="confirmModal">
    <div class="modal-content">
        <p id="modalMsg">Are you sure?</p>
        <div class="modal-btns">
            <button id="btnYes">Confirm</button>
            <button id="btnNo">Cancel</button>
        </div>
    </div>
</div>

<div class="glass-container">
<div class="brand-header">Netlink by XSU.</div>
<h1>Index of {displaypath}</h1>
<div class="controls">
    <input type="text" id="searchInput" placeholder="Search files...">
    <select id="sortSelect">
        <option value="az">A-Z</option>
        <option value="za">Z-A</option>
        <option value="newest">Newest First</option>
        <option value="oldest">Oldest First</option>
        <option value="largest">Largest First</option>
        <option value="smallest">Smallest First</option>
    </select>
</div>
<ul id="fileList">
"""
        if target_type == "file":
            name = os.path.basename(target_path)
            linkname = urllib.parse.quote(name)
            html += f'<li class="file-item" data-name="{name.lower()}" data-date="0" data-size="0" data-type="file" data-ext="file"><a class="main-link" href="/{linkname}"><span>{name}</span></a></li>\n'
        else:
            try:
                list_dir = os.listdir(path)
            except OSError:
                self.send_error(404, "No permission")
                return None
            
            if self.path != '/':
                html += '<li class="file-item" data-name=".." data-date="999999999999" data-size="-1" data-type="parent" data-ext=""><a class="main-link" href=".."><span>../ [ Back / Parent Directory ]</span></a></li>\n'
            
            for name in list_dir:
                if name == "netlink.py":
                    continue
                fullname = os.path.join(path, name)
                displayname = name
                linkname = urllib.parse.quote(name)
                try:
                    stat = os.stat(fullname)
                    mtime, size = stat.st_mtime, stat.st_size
                except OSError:
                    mtime, size = 0, 0
                
                mtime_str = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M')
                
                if os.path.isdir(fullname):
                    displayname, linkname, size = name + "/", name + "/", -1
                    html += f'<li class="file-item" data-name="{name.lower()}" data-date="{mtime}" data-size="{size}" data-type="dir" data-ext="folder"><a class="main-link" href="{linkname}"><span>{displayname}</span><span class="meta-info">{mtime_str}<br>DIR</span></a><a class="dl-btn" href="?zip={urllib.parse.quote(name)}" title="Download Folder as ZIP">⥥</a></li>\n'
                else:
                    ext = os.path.splitext(name)[1].lower()
                    if not ext: ext = "unknown"
                    
                    meta_text = ""
                    if size < 1024: meta_text = f"{size} B"
                    elif size < 1048576: meta_text = f"{size/1024:.1f} KB"
                    else: meta_text = f"{size/1048576:.1f} MB"
                    html += f'<li class="file-item" data-name="{name.lower()}" data-date="{mtime}" data-size="{size}" data-type="file" data-ext="{ext}"><a class="main-link" href="{linkname}"><span>{displayname}</span><span class="meta-info">{mtime_str}<br>{meta_text}</span></a></li>\n'
        
        html += """</ul>
</div>
<script>
let animIdx = 0;
const frames = ['( =.=)', '( >.<)', '( =.=)', '(>.< )', '(=.= )', '(>ᴗ<)', '(=ᴗ=)', '(>ᴗ<)'];
setInterval(() => {
    document.getElementById('ascii-anim').innerText = frames[animIdx];
    animIdx = (animIdx + 1) % frames.length;
}, 600);

const root = document.documentElement;
const searchInput = document.getElementById('searchInput');
const sortSelect = document.getElementById('sortSelect');
const fileList = document.getElementById('fileList');
const settingsBtn = document.getElementById('settingsBtn');
const settingsPanel = document.getElementById('settingsPanel');
const colorPicker = document.getElementById('colorPicker');
const fontSizeSlider = document.getElementById('fontSizeSlider');
const deepScanCheck = document.getElementById('deepScanCheck');
const sectionTypeCheck = document.getElementById('sectionTypeCheck');
const confFolderCheck = document.getElementById('confFolderCheck');
const confFileCheck = document.getElementById('confFileCheck');

const modal = document.getElementById('confirmModal');
const modalMsg = document.getElementById('modalMsg');
const btnYes = document.getElementById('btnYes');
const btnNo = document.getElementById('btnNo');

let items = Array.from(document.querySelectorAll('.file-item'));
let pendingNavUrl = null;

settingsBtn.addEventListener('click', () => { settingsPanel.classList.toggle('active'); });
colorPicker.addEventListener('input', (e) => { root.style.setProperty('--accent-color', e.target.value); });
fontSizeSlider.addEventListener('input', (e) => { root.style.setProperty('--font-size', e.target.value + 'px'); });

function showConfirm(msg, url) {
    modalMsg.innerText = msg;
    pendingNavUrl = url;
    modal.classList.add('active');
}

btnNo.addEventListener('click', () => { modal.classList.remove('active'); pendingNavUrl = null; });
btnYes.addEventListener('click', () => {
    if (pendingNavUrl) window.location.href = pendingNavUrl;
    modal.classList.remove('active');
    pendingNavUrl = null;
});

document.addEventListener('click', (e) => {
    const dlBtn = e.target.closest('.dl-btn');
    const mainLink = e.target.closest('.main-link');

    if (dlBtn && confFolderCheck.checked) {
        e.preventDefault();
        showConfirm("Archive and download this folder as a .ZIP?", dlBtn.href);
    } else if (mainLink) {
        const li = mainLink.closest('.file-item');
        if (li && li.getAttribute('data-type') === 'file' && confFileCheck.checked) {
            e.preventDefault();
            showConfirm("Initiate download for this file?", mainLink.href);
        }
    }
});

function renderList() {
    fileList.innerHTML = '';
    
    if (sectionTypeCheck.checked) {
        let currentExt = null;
        items.forEach(item => {
            if (item.style.display === 'none') return;
            const type = item.getAttribute('data-type');
            const ext = type === 'dir' ? 'Folders' : (type === 'parent' ? 'System' : item.getAttribute('data-ext'));
            
            if (ext !== currentExt) {
                const header = document.createElement('li');
                header.className = 'section-header';
                header.innerText = ext;
                fileList.appendChild(header);
                currentExt = ext;
            }
            fileList.appendChild(item);
        });
    } else {
        items.forEach(item => {
            if (item.style.display !== 'none') fileList.appendChild(item);
        });
    }
}

function doSort() {
    const mode = sortSelect.value;
    const isSectioned = sectionTypeCheck.checked;

    items.sort((a, b) => {
        const typeA = a.getAttribute('data-type');
        const typeB = b.getAttribute('data-type');
        
        if (typeA === 'parent') return -1;
        if (typeB === 'parent') return 1;

        if (isSectioned) {
            const extA = typeA === 'dir' ? '0_folder' : a.getAttribute('data-ext');
            const extB = typeB === 'dir' ? '0_folder' : b.getAttribute('data-ext');
            if (extA !== extB) return extA.localeCompare(extB);
        } else {
            if (typeA === 'dir' && typeB === 'file') return -1;
            if (typeA === 'file' && typeB === 'dir') return 1;
        }

        const nameA = a.getAttribute('data-name'), nameB = b.getAttribute('data-name');
        const dateA = parseFloat(a.getAttribute('data-date')), dateB = parseFloat(b.getAttribute('data-date'));
        const sizeA = parseFloat(a.getAttribute('data-size')), sizeB = parseFloat(b.getAttribute('data-size'));

        if (mode === 'az') return nameA.localeCompare(nameB);
        if (mode === 'za') return nameB.localeCompare(nameA);
        if (mode === 'newest') return dateB - dateA;
        if (mode === 'oldest') return dateA - dateB;
        if (mode === 'largest') return sizeB - sizeA;
        if (mode === 'smallest') return sizeA - sizeB;
    });
    renderList();
}

sectionTypeCheck.addEventListener('change', doSort);
sortSelect.addEventListener('change', doSort);

searchInput.addEventListener('input', async (e) => {
    const term = e.target.value.toLowerCase();
    const isDeepscan = deepScanCheck.checked;

    if (isDeepscan && term.length > 0) {
        try {
            const response = await fetch('?deepscan=' + encodeURIComponent(term));
            const data = await response.json();
            items = [];
            data.forEach(item => {
                const li = document.createElement('li');
                li.className = 'file-item';
                li.setAttribute('data-name', item.name.toLowerCase());
                li.setAttribute('data-date', item.date);
                li.setAttribute('data-size', item.size);
                
                const extMatch = item.name.match(/\.[0-9a-z]+$/i);
                li.setAttribute('data-type', 'file');
                li.setAttribute('data-ext', extMatch ? extMatch[0].toLowerCase() : 'unknown');

                let sizeText = "";
                if (item.size < 1024) sizeText = item.size + " B";
                else if (item.size < 1048576) sizeText = (item.size/1024).toFixed(1) + " KB";
                else sizeText = (item.size/1048576).toFixed(1) + " MB";
                
                const dateText = new Date(item.date * 1000).toISOString().replace('T', ' ').substring(0, 16);

                li.innerHTML = `<a href="${encodeURI(item.name)}" class="main-link"><span>${item.name}</span><span class="meta-info">${dateText}<br>${sizeText}</span></a>`;
                items.push(li);
            });
            doSort();
        } catch(err) {}
    } else {
        if (isDeepscan && term.length === 0) {
            window.location.reload();
        } else {
            items.forEach(item => {
                const name = item.getAttribute('data-name');
                item.style.display = (name === '..' || name.includes(term)) ? '' : 'none';
            });
            renderList();
        }
    }
});

doSort(); 
</script>
</body>
</html>
"""
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode('utf-8', 'surrogateescape'))

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

def main():
    global target_path, target_type, accent_color
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", type=str)
    parser.add_argument("--type", choices=["dir", "file"])
    parser.add_argument("--color", type=str, default="#ffe8a8")
    args = parser.parse_args()

    accent_color = args.color
    print(RED + ASCII_ART + RESET)

    if args.path and args.type:
        target_path = os.path.abspath(args.path)
        target_type = args.type
        os.chdir(target_path if target_type == "dir" else os.path.dirname(target_path))
    else:
        print("1. Serve Entire Directory\n2. Serve Single File\n3. Serve Whole Device Storage")
        try:
            choice = input("\nSelection:").strip()
        except KeyboardInterrupt: sys.exit(0)
        
        current_dir = os.getcwd()
        items = sorted(os.listdir(current_dir))
        
        if choice == "1":
            target_type = "dir"
            dirs = ["."] + [d for d in items if os.path.isdir(d)]
            for i, d in enumerate(dirs): print(f"{i}. {d}")
            idx = int(input("Select number: ").strip())
            target_path = os.path.abspath(dirs[idx])
            os.chdir(target_path)
        elif choice == "2":
            target_type = "file"
            files = [f for f in items if os.path.isfile(f) and f != "netlink.py"]
            for i, f in enumerate(files): print(f"{i}. {f}")
            idx = int(input("Select number: ").strip())
            target_path = os.path.abspath(files[idx])
            os.chdir(os.path.dirname(target_path))
        elif choice == "3":
            target_type = "dir"
            target_path = "/storage/emulated/0" if os.path.exists("/storage/emulated/0") else "/sdcard" if os.path.exists("/sdcard") else os.path.abspath(os.sep)
            os.chdir(target_path)
        else: sys.exit(1)

    with socketserver.ThreadingTCPServer(("", 8000), GlassHandler) as httpd:
        print(f"\nServer Address: http://{get_local_ip()}:8000\n")
        try: httpd.serve_forever()
        except KeyboardInterrupt: sys.exit(0)

if __name__ == "__main__":
    main()
