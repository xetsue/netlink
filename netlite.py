import os
import socket
import http.server
import socketserver
import urllib.parse
import sys

class LiteStreamHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            self.list_directory(path)
        elif os.path.isfile(path):
            self.stream_file(path)
        else:
            self.send_error(404, "File Not Found")

    def translate_path(self, path):
        path = urllib.parse.unquote(path).split('?', 1)[0].split('#', 1)[0]
        path = os.path.normpath(path).lstrip('/')
        return os.path.abspath(os.path.join(os.getcwd(), path))

    def stream_file(self, path):
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

    def list_directory(self, path):
        try:
            items = os.listdir(path)
        except OSError:
            self.send_error(403, "Permission Denied")
            return
        
        items.sort(key=lambda x: x.lower())
        html = f"<html><head><meta name='viewport' content='width=device-width, initial-scale=1'><style>body{{font-family:sans-serif;padding:20px;background:#fff;color:#000}}a{{display:block;padding:12px;color:#000;text-decoration:none;border-bottom:1px solid #ccc}}</style></head><body><h3>{self.path}</h3>"
        if self.path != "/":
            html += "<a href='..'>[ Back ]</a>"
        for item in items:
            if item == "netlink.py": continue
            is_dir = os.path.isdir(os.path.join(path, item))
            display_name = item + ("/" if is_dir else "")
            html += f"<a href='{urllib.parse.quote(item)}'>{display_name}</a>"
        html += "</body></html>"
        
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(html.encode())

def get_ip():
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
    print("[ Netlink Lite Streamer ]")
    print("1. Current Folder\n2. Device Storage")
    choice = input("Select: ").strip()
    
    root = "/storage/emulated/0" if choice == "2" and os.path.exists("/storage/emulated/0") else os.getcwd()
    if choice == "2" and not os.path.exists("/storage/emulated/0"):
        root = os.path.abspath(os.sep)
        
    os.chdir(root)
    server_address = ("", 8000)
    
    with socketserver.ThreadingTCPServer(server_address, LiteStreamHandler) as httpd:
        print(f"Running at http://{get_ip()}:8000")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            sys.exit(0)

if __name__ == "__main__":
    main()
