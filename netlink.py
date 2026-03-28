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
accent_color = "#ffffff"
custom_color_flag = "false"

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
            matches = []
            count = 0
            try:
                for root, dirs, files in os.walk(path):
                    for name in dirs + files:
                        name_lower = name.lower()
                        if term in name_lower:
                            full_path = os.path.join(root, name)
                            rel_path = os.path.relpath(full_path, path)
                            is_dir = name in dirs
                            try:
                                stat = os.stat(full_path)
                                size, mtime = stat.st_size, stat.st_mtime
                            except Exception:
                                size, mtime = 0, 0
                            
                            if is_dir:
                                size = -1
                                
                            name_no_ext = os.path.splitext(name_lower)[0]
                            if name_lower == term:
                                score = 0
                            elif name_no_ext == term:
                                score = 1
                            elif name_lower.startswith(term):
                                score = 2
                            else:
                                score = 3
                                
                            matches.append({"name": rel_path.replace('\\', '/'), "size": size, "date": mtime, "type": "dir" if is_dir else "file", "score": score, "basename": name_lower})
                            count += 1
                            if count >= 5000:
                                break
                    if count >= 5000:
                        break
            except Exception:
                pass

            matches.sort(key=lambda x: (x["score"], len(x["basename"]), x["name"]))
            results = matches[:1000]
            for r in results:
                r.pop("basename", None)

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            try:
                self.wfile.write(json.dumps(results).encode('utf-8'))
            except (BrokenPipeError, ConnectionResetError):
                pass
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
        except (BrokenPipeError, ConnectionResetError):
            pass
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
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>Netlink by XSU.</title>
<style>
:root {{
    --accent-color: {accent_color};
    --font-size: 16px;
}}
body {{ background-color: #050505; color: #f0f0f0; font-family: monospace; margin: 0; padding: 20px; display: flex; justify-content: center; min-height: 100vh; font-size: var(--font-size); overflow-x: hidden; box-sizing: border-box; }}
#ascii-anim {{ position: fixed; top: 20px; left: 20px; font-size: 1.5em; color: var(--accent-color); z-index: 1000; font-weight: bold; text-shadow: 0 0 10px rgba(255,255,255,0.2); }}
.top-bar {{ position: fixed; top: 20px; right: 20px; z-index: 1000; }}
.settings-btn {{ background: rgba(255,255,255,0.05); border: 1px solid var(--accent-color); color: #fff; padding: 10px 15px; border-radius: 8px; cursor: pointer; font-size: 1.5em; backdrop-filter: blur(10px); display: flex; align-items: center; justify-content: center; width: 50px; height: 50px; transition: all 0.3s ease; }}
.settings-btn:hover {{ background: rgba(255,255,255,0.1); transform: scale(1.05); }}
.settings-panel {{ display: none; position: absolute; top: 60px; right: 0; width: 300px; background: rgba(10,10,10,0.8); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 30px; box-shadow: 0 10px 40px rgba(0,0,0,0.7); flex-direction: column; gap: 20px; max-height: 80vh; overflow-y: auto; box-sizing: border-box; }}
.settings-panel.active {{ display: flex; }}
.setting-item {{ display: flex; justify-content: space-between; align-items: center; color: #ccc; font-size: 0.9em; }}
.setting-item span {{ flex-shrink: 0; }}
.setting-item select {{ background: rgba(255,255,255,0.05); color: #fff; border: 1px solid rgba(255,255,255,0.2); padding: 5px; border-radius: 4px; outline: none; }}
.setting-item select option {{ background: #111; }}
.setting-item input[type="color"] {{ background: none; border: 1px solid rgba(255,255,255,0.2); border-radius: 4px; cursor: pointer; height: 35px; width: 50px; padding: 0; }}
.setting-item input[type="range"] {{ flex-grow: 1; margin-left: 15px; accent-color: var(--accent-color); }}
.setting-item input[type="checkbox"] {{ width: 20px; height: 20px; cursor: pointer; accent-color: #007bff; }}
.glass-container {{ background: rgba(255, 255, 255, 0.03); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 16px; padding: 40px; width: 100%; max-width: 1400px; box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5); display: flex; flex-direction: column; margin-top: 60px; box-sizing: border-box; overflow: hidden; }}
.brand-header {{ font-size: 1.5em; color: #ffffff; text-align: center; margin-bottom: 30px; letter-spacing: 2px; border-bottom: 2px solid var(--accent-color); padding-bottom: 20px; font-weight: bold; opacity: 0.9; }}
h1 {{ border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 20px; margin-top: 0; font-size: 1.1em; letter-spacing: 1px; color: #aaa; word-break: break-all; }}
.controls {{ display: flex; gap: 15px; margin-bottom: 30px; flex-wrap: wrap; }}
.controls input, .controls select {{ background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.2); color: #fff; padding: 15px; border-radius: 8px; font-family: monospace; font-size: 1em; outline: none; transition: border-color 0.3s ease; width: 100%; box-sizing: border-box; }}
.controls input {{ flex-grow: 1; }}
.controls input:focus, .controls select:focus {{ background: rgba(255,255,255,0.1); border-color: var(--accent-color); }}
.controls select option {{ background: #111; color: #fff; }}
@media (min-width: 768px) {{
    .controls input, .controls select {{ width: auto; }}
}}
ul {{ list-style-type: none; padding: 0; margin: 0; }}
li {{ display: flex; gap: 10px; margin: 15px 0; align-items: stretch; flex-wrap: nowrap; }}
li.section-header {{ color: var(--accent-color); font-size: 1.2em; font-weight: bold; border-bottom: 1px dashed rgba(255,255,255,0.2); padding-bottom: 10px; margin-top: 40px; text-transform: uppercase; letter-spacing: 1px; width: 100%; }}
a {{ text-decoration: none; transition: all 0.3s ease; background: rgba(255,255,255,0.02); }}
.main-link {{ flex-grow: 1; color: var(--accent-color); display: flex; justify-content: space-between; align-items: center; min-width: 0; width: 100%; box-sizing: border-box; }}
.main-link:hover {{ background: rgba(255,255,255,0.08); color: #fff; border-color: rgba(255,255,255,0.2); transform: translateX(8px); }}

.name-wrapper {{ flex-grow: 1; min-width: 0; margin-right: 15px; overflow: hidden; display: flex; flex-direction: column; justify-content: center; align-items: flex-start; }}
.name-text {{ display: inline-block; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%; vertical-align: middle; }}
.path-text {{ display: inline-block; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%; font-size: 0.75em; color: #888; margin-top: 4px; }}
.main-link:hover .name-text, .main-link:hover .path-text {{ text-overflow: clip; max-width: none; animation: scrollText 4s linear infinite alternate; }}

@keyframes scrollText {{
    0% {{ transform: translateX(0); }}
    100% {{ transform: translateX(-150px); }}
}}
@keyframes pulse {{
    0% {{ opacity: 0.6; transform: scale(0.98); }}
    50% {{ opacity: 1; transform: scale(1); }}
    100% {{ opacity: 0.6; transform: scale(0.98); }}
}}

.file-item[data-type="dir"] .main-link {{ border: 1px solid var(--accent-color); padding: 15px 20px; border-radius: 8px; }}
.file-item[data-type="file"] .main-link {{ border: 1px solid transparent; padding: 15px 20px; border-radius: 4px; }}
.file-item[data-type="parent"] .main-link {{ border: 1px solid transparent; padding: 15px 20px; border-radius: 8px; color: #ffffff; font-weight: bold; }}

.dl-btn {{ color: var(--accent-color); display: flex; align-items: center; justify-content: center; padding: 15px; font-size: 1.4em; border-radius: 8px; border: 1px solid transparent; flex-shrink: 0; }}
.dl-btn:hover {{ background: rgba(255,255,255,0.08); color: #fff; border-color: rgba(255,255,255,0.2); transform: scale(1.05); }}
.meta-info {{ color: #888; font-size: 0.85em; text-align: right; flex-shrink: 0; white-space: nowrap; }}
.modal {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); z-index: 2000; align-items: center; justify-content: center; backdrop-filter: blur(8px); }}
.modal.active {{ display: flex; }}
.modal-content {{ background: rgba(15,15,15,0.95); border: 1px solid var(--accent-color); padding: 30px; border-radius: 12px; text-align: center; box-shadow: 0 10px 50px rgba(0,0,0,0.8); width: 90%; max-width: 400px; box-sizing: border-box; }}
.modal-content p {{ font-size: 1.1em; margin-bottom: 30px; color: #fff; }}
.modal-btns {{ display: flex; gap: 15px; justify-content: center; flex-wrap: wrap; }}
.modal-btns button {{ background: rgba(255,255,255,0.05); color: #fff; border: 1px solid var(--accent-color); padding: 12px 20px; border-radius: 8px; cursor: pointer; font-family: monospace; font-size: 1em; transition: 0.3s; flex-grow: 1; }}
.modal-btns button:hover {{ background: var(--accent-color); color: #000; font-weight: bold; }}

@media (max-width: 600px) {{
    body {{ padding: 10px; }}
    .glass-container {{ padding: 20px; margin-top: 70px; }}
    .settings-panel {{ width: calc(100vw - 20px); right: -10px; }}
    .main-link {{ flex-direction: column; align-items: flex-start; gap: 10px; }}
    .meta-info {{ text-align: left; width: 100%; }}
    .name-wrapper {{ margin-right: 0; width: 100%; }}
    .dl-btn {{ border: 1px solid rgba(255,255,255,0.1); }}
}}
</style>
</head>
<body>
<div id="ascii-anim">(=.=)</div>
<div class="top-bar">
    <button class="settings-btn" id="settingsBtn">⋰</button>
    <div class="settings-panel" id="settingsPanel">
        <div class="setting-item">
            <span>Group Priority</span>
            <select id="groupPriority">
                <option value="folders">Folders First</option>
                <option value="files">Files First</option>
                <option value="none">None</option>
            </select>
        </div>
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
            html += f'<li class="file-item" data-name="{name.lower()}" data-date="0" data-size="0" data-type="file" data-ext="file" data-score="4"><a class="main-link" href="/{linkname}"><div class="name-wrapper"><span class="name-text">{name}</span></div></a></li>\n'
        else:
            try:
                list_dir = os.listdir(path)
            except OSError:
                self.send_error(404, "No permission")
                return None
            
            if self.path != '/':
                html += '<li class="file-item" data-name=".." data-date="999999999999" data-size="-1" data-type="parent" data-ext="" data-score="-1"><a class="main-link" href=".."><div class="name-wrapper"><span class="name-text">[ &laquo; Back ]</span></div></a></li>\n'
            
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
                    html += f'<li class="file-item" data-name="{name.lower()}" data-date="{mtime}" data-size="{size}" data-type="dir" data-ext="folder" data-score="4"><a class="main-link" href="{linkname}"><div class="name-wrapper"><span class="name-text">{displayname}</span></div><span class="meta-info">{mtime_str}<br>DIR</span></a><a class="dl-btn" href="?zip={urllib.parse.quote(name)}" title="Download Folder as ZIP">⥥</a></li>\n'
                else:
                    ext = os.path.splitext(name)[1].lower()
                    if not ext: ext = "unknown"
                    
                    meta_text = ""
                    if size < 1024: meta_text = f"{size} B"
                    elif size < 1048576: meta_text = f"{size/1024:.1f} KB"
                    else: meta_text = f"{size/1048576:.1f} MB"
                    html += f'<li class="file-item" data-name="{name.lower()}" data-date="{mtime}" data-size="{size}" data-type="file" data-ext="{ext}" data-score="4"><a class="main-link" href="{linkname}"><div class="name-wrapper"><span class="name-text">{displayname}</span></div><span class="meta-info">{mtime_str}<br>{meta_text}</span></a></li>\n'
        
        html += """</ul>
</div>
<script>
const customColorFlag = """ + custom_color_flag + """;
const backendColor = '""" + accent_color + """';
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
const groupPriority = document.getElementById('groupPriority');

const modal = document.getElementById('confirmModal');
const modalMsg = document.getElementById('modalMsg');
const btnYes = document.getElementById('btnYes');
const btnNo = document.getElementById('btnNo');

let items = Array.from(document.querySelectorAll('.file-item'));
let pendingNavUrl = null;
let searchTimeout = null;
let searchController = null;

function loadSettings() {
    const saved = JSON.parse(localStorage.getItem('netlinkConfig') || '{}');
    if (saved.groupPriority) groupPriority.value = saved.groupPriority;
    if (saved.sortSelect) sortSelect.value = saved.sortSelect;
    if (saved.fontSizeSlider) {
        fontSizeSlider.value = saved.fontSizeSlider;
        root.style.setProperty('--font-size', saved.fontSizeSlider + 'px');
    }
    if (saved.deepScanCheck !== undefined) deepScanCheck.checked = saved.deepScanCheck;
    if (saved.sectionTypeCheck !== undefined) sectionTypeCheck.checked = saved.sectionTypeCheck;
    if (saved.confFolderCheck !== undefined) confFolderCheck.checked = saved.confFolderCheck;
    if (saved.confFileCheck !== undefined) confFileCheck.checked = saved.confFileCheck;
    
    if (customColorFlag) {
        colorPicker.value = backendColor;
        root.style.setProperty('--accent-color', backendColor);
        saveSettings();
    } else if (saved.colorPicker) {
        colorPicker.value = saved.colorPicker;
        root.style.setProperty('--accent-color', saved.colorPicker);
    }
}

function saveSettings() {
    const config = {
        groupPriority: groupPriority.value,
        sortSelect: sortSelect.value,
        colorPicker: colorPicker.value,
        fontSizeSlider: fontSizeSlider.value,
        deepScanCheck: deepScanCheck.checked,
        sectionTypeCheck: sectionTypeCheck.checked,
        confFolderCheck: confFolderCheck.checked,
        confFileCheck: confFileCheck.checked
    };
    localStorage.setItem('netlinkConfig', JSON.stringify(config));
}

settingsBtn.addEventListener('click', () => { settingsPanel.classList.toggle('active'); });

[groupPriority, deepScanCheck, sectionTypeCheck, confFolderCheck, confFileCheck, sortSelect].forEach(el => {
    el.addEventListener('change', () => { saveSettings(); doSort(); });
});

colorPicker.addEventListener('input', (e) => {
    root.style.setProperty('--accent-color', e.target.value);
    saveSettings();
});

fontSizeSlider.addEventListener('input', (e) => {
    root.style.setProperty('--font-size', e.target.value + 'px');
    saveSettings();
});

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
    const groupMode = groupPriority.value;
    const searchTerm = searchInput.value.toLowerCase();
    const isSearching = deepScanCheck.checked && searchTerm.length > 0;

    items.sort((a, b) => {
        const typeA = a.getAttribute('data-type');
        const typeB = b.getAttribute('data-type');
        
        if (typeA === 'parent') return -1;
        if (typeB === 'parent') return 1;

        if (isSearching) {
            const scoreA = parseInt(a.getAttribute('data-score') || '4');
            const scoreB = parseInt(b.getAttribute('data-score') || '4');
            if (scoreA !== scoreB) return scoreA - scoreB;
        }

        if (isSectioned) {
            const extA = typeA === 'dir' ? '0_folder' : a.getAttribute('data-ext');
            const extB = typeB === 'dir' ? '0_folder' : b.getAttribute('data-ext');
            if (extA !== extB) return extA.localeCompare(extB);
        } else {
            if (groupMode === 'folders') {
                if (typeA === 'dir' && typeB === 'file') return -1;
                if (typeA === 'file' && typeB === 'dir') return 1;
            } else if (groupMode === 'files') {
                if (typeA === 'file' && typeB === 'dir') return -1;
                if (typeA === 'dir' && typeB === 'file') return 1;
            }
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

searchInput.addEventListener('input', (e) => {
    clearTimeout(searchTimeout);
    const term = e.target.value.toLowerCase();
    const isDeepscan = deepScanCheck.checked;

    if (isDeepscan && term.length > 0) {
        fileList.innerHTML = '<li style="justify-content: center; color: var(--accent-color); padding: 40px; font-weight: bold; animation: pulse 1.5s infinite; border: 1px solid rgba(255,255,255,0.1); border-radius: 8px;">Deepscanning storage... Please wait.</li>';
        
        searchTimeout = setTimeout(async () => {
            if (searchController) searchController.abort();
            searchController = new AbortController();
            
            try {
                const response = await fetch('?deepscan=' + encodeURIComponent(term), { signal: searchController.signal });
                const data = await response.json();
                items = [];
                data.forEach(item => {
                    const li = document.createElement('li');
                    li.className = 'file-item';
                    li.setAttribute('data-name', item.name.toLowerCase());
                    li.setAttribute('data-date', item.date);
                    li.setAttribute('data-size', item.size);
                    li.setAttribute('data-score', item.score !== undefined ? item.score : 4);
                    
                    const isDir = item.type === 'dir';
                    const extMatch = !isDir ? item.name.match(/\\.[0-9a-z]+$/i) : null;
                    li.setAttribute('data-type', isDir ? 'dir' : 'file');
                    li.setAttribute('data-ext', isDir ? 'folder' : (extMatch ? extMatch[0].toLowerCase() : 'unknown'));

                    let sizeText = "";
                    if (isDir) sizeText = "DIR";
                    else if (item.size < 1024) sizeText = item.size + " B";
                    else if (item.size < 1048576) sizeText = (item.size/1024).toFixed(1) + " KB";
                    else sizeText = (item.size/1048576).toFixed(1) + " MB";
                    
                    const dateText = new Date(item.date * 1000).toISOString().replace('T', ' ').substring(0, 16);
                    
                    const fullPath = item.name;
                    const baseName = fullPath.split('/').pop() + (isDir ? '/' : '');
                    const linkName = encodeURI(fullPath) + (isDir ? '/' : '');

                    let inner = `<a href="${linkName}" class="main-link"><div class="name-wrapper"><span class="name-text">${baseName}</span><span class="path-text">${fullPath}</span></div><span class="meta-info">${dateText}<br>${sizeText}</span></a>`;
                    
                    if (isDir) {
                        inner += `<a class="dl-btn" href="?zip=${encodeURIComponent(fullPath)}" title="Download Folder as ZIP">⥥</a>`;
                    }
                    
                    li.innerHTML = inner;
                    items.push(li);
                });
                fileList.innerHTML = '';
                doSort();
            } catch(err) {
                if (err.name !== 'AbortError') {
                    fileList.innerHTML = '<li style="justify-content: center; color: #ff5555; padding: 40px;">Search failed. Please try again.</li>';
                }
            }
        }, 400); 
    } else {
        if (searchController) searchController.abort();
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

loadSettings();
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
    global target_path, target_type, accent_color, custom_color_flag
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", type=str)
    parser.add_argument("--type", choices=["dir", "file"])
    parser.add_argument("--color", type=str, default=None)
    args = parser.parse_args()

    if args.color:
        accent_color = args.color
        custom_color_flag = "true"
    else:
        accent_color = "#ffffff"
        custom_color_flag = "false"

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

    socketserver.ThreadingTCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(("", 8000), GlassHandler) as httpd:
        print(f"\nServer Address: http://{get_local_ip()}:8000\nhttp://0.0.0.0:8000\n")
        try: 
            httpd.serve_forever()
        except KeyboardInterrupt: 
            pass
        finally:
            httpd.server_close()
            sys.exit(0)

if __name__ == "__main__":
    main()
