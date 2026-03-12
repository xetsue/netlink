import os
import socket
import http.server
import socketserver
import urllib.parse
import sys
import argparse

target_path = ""
target_type = ""
accent_color = "#00ffcc"
RED = "\033[91m"
RESET = "\033[0m"
ASCII_ART = r"""
 
 __  __     ______     __  __    
/\_\_\_\   /   ___\   /\ \/\ \   
\/_/\_\/_  \ \___  \  \ \ \_\ \  
  /\_\/\_\  \/\_____\  \ \_____\ 
  \/_/\/_/   \/_____/   \/_____/
  
  [   Netlink â€” Necessary Speed   ] 
"""

class GlassHandler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        if target_type == "file":
            if path == "/":
                return os.path.dirname(target_path)
            elif path == "/" + urllib.parse.quote(os.path.basename(target_path)):
                return target_path
            else:
                return ""
        return super().translate_path(path)

    def list_directory(self, path):
        displaypath = urllib.parse.unquote(self.path)
        
        html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Netlink by XSU.</title>
<style>
body {{ background-color: #050505; color: #f0f0f0; font-family: monospace; margin: 0; padding: 4vw; display: flex; justify-content: center; min-height: 100vh; font-size: clamp(12px, 2.5vw, 20px); }}
.glass-container {{ background: rgba(255, 255, 255, 0.03); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 16px; padding: 40px; width: 100%; max-width: 1200px; box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5); display: flex; flex-direction: column; }}
.brand-header {{ font-size: 1.5em; color: #ffffff; text-align: center; margin-bottom: 30px; letter-spacing: 2px; border-bottom: 2px solid {accent_color}33; padding-bottom: 20px; font-weight: bold; }}
h1 {{ border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 20px; margin-top: 0; font-size: 1em; letter-spacing: 1px; color: #aaa; }}
.controls {{ display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; }}
.controls input, .controls select {{ background: rgba(255,255,255,0.05); border: 1px solid {accent_color}4D; color: #fff; padding: 12px; border-radius: 8px; font-family: monospace; font-size: 1em; outline: none; }}
.controls input {{ flex-grow: 1; }}
.controls input:focus, .controls select:focus {{ background: rgba(255,255,255,0.1); border-color: {accent_color}; }}
.controls select option {{ background: #111; color: #fff; }}
ul {{ list-style-type: none; padding: 0; margin: 0; }}
li {{ margin: 15px 0; }}
a {{ color: {accent_color}; text-decoration: none; display: flex; justify-content: space-between; padding: 20px; border-radius: 8px; border: 1px solid transparent; transition: all 0.3s ease; background: rgba(255,255,255,0.02); word-wrap: break-word; }}
a:hover {{ background: rgba(255,255,255,0.08); color: #fff; border-color: {accent_color}4D; transform: translateX(8px); }}
.meta-info {{ color: #888; font-size: 0.8em; }}
</style>
</head>
<body>
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
            html += f'<li class="file-item" data-name="{name.lower()}" data-date="0" data-size="0"><a href="/{linkname}"><span>{name}</span></a></li>\n'
        else:
            try:
                list_dir = os.listdir(path)
            except OSError:
                self.send_error(404, "No permission")
                return None
            
            if self.path != '/':
                html += '<li class="file-item" data-name=".." data-date="999999999999" data-size="-1"><a href=".."><span>../ (Parent Directory)</span></a></li>\n'
            
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
                
                meta_text = ""
                if os.path.isdir(fullname):
                    displayname, linkname, size = name + "/", name + "/", -1
                else:
                    if size < 1024: meta_text = f"{size} B"
                    elif size < 1048576: meta_text = f"{size/1024:.1f} KB"
                    else: meta_text = f"{size/1048576:.1f} MB"

                html += f'<li class="file-item" data-name="{name.lower()}" data-date="{mtime}" data-size="{size}"><a href="{linkname}"><span>{displayname}</span><span class="meta-info">{meta_text}</span></a></li>\n'
        
        html += """</ul>
</div>
<script>
const searchInput = document.getElementById('searchInput');
const sortSelect = document.getElementById('sortSelect');
const fileList = document.getElementById('fileList');
let items = Array.from(document.querySelectorAll('.file-item'));

searchInput.addEventListener('input', (e) => {
    const term = e.target.value.toLowerCase();
    items.forEach(item => {
        const name = item.getAttribute('data-name');
        item.style.display = (name === '..' || name.includes(term)) ? '' : 'none';
    });
});

sortSelect.addEventListener('change', (e) => {
    const mode = e.target.value;
    items.sort((a, b) => {
        const nameA = a.getAttribute('data-name'), nameB = b.getAttribute('data-name');
        if (nameA === '..') return -1; if (nameB === '..') return 1;
        
        const dateA = parseFloat(a.getAttribute('data-date')), dateB = parseFloat(b.getAttribute('data-date'));
        const sizeA = parseFloat(a.getAttribute('data-size')), sizeB = parseFloat(b.getAttribute('data-size'));

        if (mode === 'az') return nameA.localeCompare(nameB);
        if (mode === 'za') return nameB.localeCompare(nameA);
        if (mode === 'newest') return dateB - dateA;
        if (mode === 'oldest') return dateA - dateB;
        if (mode === 'largest') return sizeB - sizeA;
        if (mode === 'smallest') return sizeA - sizeB;
    });
    fileList.innerHTML = '';
    items.forEach(item => fileList.appendChild(item));
});
</script>
</body>
</html>
"""
        encoded = html.encode('utf-8', 'surrogateescape')
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)
        return None

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
    parser.add_argument("--path", type=str, help="Path to serve")
    parser.add_argument("--type", choices=["dir", "file"], help="Type of target")
    parser.add_argument("--color", type=str, default="#00ffcc", help="Accent color hex code")
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

    with socketserver.TCPServer(("", 8000), GlassHandler) as httpd:
        print(f"\nServer Address: http://{get_local_ip()}:8000\n")
        try: httpd.serve_forever()
        except KeyboardInterrupt: sys.exit(0)

if __name__ == "__main__":
    main()
