from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from functools import partial
import os
import ssl
import sys

serverName = '0.0.0.0'
serverPortHTTP = 8000 #for base HTTP
serverPortHTTPS = 4443 #for HTTPS
isHTTPS = True

# All paths are resolved relative to this file, so the server works no matter
# which folder it is started from.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CERT_FILE = os.path.join(BASE_DIR, 'cert.pem')
KEY_FILE = os.path.join(BASE_DIR, 'key.pem')

# Relative URL of the resume, served from the resume/ folder next to this file
rfile = "resume/Resume.pdf"

WebContent = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Resume Webpage</title>
    <style>
        .pdf-container {{ width: 100%; height: 90vh; }}
    </style>
</head>
<body>
    <h1>Found below is Erick's resume:</h1>
    <embed class="pdf-container" src="{rfile}" type="application/pdf">
</body>
</html>
"""
WebBytes = WebContent.encode("utf-8")

class WebServer(SimpleHTTPRequestHandler):
    def _is_homepage(self):
        path = self.path.split('?', 1)[0]
        return path in ('/', '/index.html')

    def _send_homepage_headers(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(WebBytes)))
        self.end_headers()

    def do_GET(self):
        if self._is_homepage():
            self._send_homepage_headers()
            self.wfile.write(WebBytes)
        else:
            # Serve real files (e.g., resume/Resume.pdf) or return 404
            super().do_GET()

    def do_HEAD(self):
        # HEAD must return the same headers as GET, with no body
        if self._is_homepage():
            self._send_homepage_headers()
        else:
            super().do_HEAD()

    def _read_body(self):
        """Returns the request body, or None after sending an error response."""
        content_length = self.headers.get('Content-Length')
        if content_length is None:
            self.send_response(411, "Length Required")
            self.end_headers()
            return None
        try:
            length = int(content_length)
            if length < 0:
                raise ValueError
        except ValueError:
            self.send_response(400, "Bad Request")
            self.end_headers()
            self.wfile.write(b"Error: Invalid Content-Length header.")
            return None
        return self.rfile.read(length)

    def do_POST(self):
        post_data = self._read_body()
        if post_data is None:
            return

        message = b"Server: POST Received"
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.send_header("Content-Length", str(len(message)))
        self.end_headers()

        print(f"Raw Data: {post_data}")
        self.wfile.write(message)

    def do_PUT(self):
        filename = os.path.basename(self.path.split('?', 1)[0])

        if not filename:
            self.send_response(400, "Bad Request")
            self.end_headers()
            self.wfile.write(b"Error: Missing filename in URI path.")
            return

        file_data = self._read_body()
        if file_data is None:
            return

        # basename() above blocks path traversal (e.g., /../../file)
        with open(os.path.join(BASE_DIR, filename), 'wb') as output_file:
            output_file.write(file_data)

        message = f"Successfully saved payload to: {filename}\n".encode('utf-8')
        self.send_response(201, "Created")
        self.send_header("Content-Length", str(len(message)))
        self.end_headers()
        self.wfile.write(message)

    def end_headers(self):
        self.send_header('Cache-Control', 'public, max-age=20')
        super().end_headers()

def Active_Server():
    port = serverPortHTTPS if isHTTPS else serverPortHTTP
    serverAddress = (serverName, port)

    # Serve files from this file's folder; threaded so a browser loading the
    # page and the PDF at the same time (or the cache) never blocks
    handler = partial(WebServer, directory=BASE_DIR)
    Http = ThreadingHTTPServer(serverAddress, handler)

    if isHTTPS:
        if not (os.path.exists(CERT_FILE) and os.path.exists(KEY_FILE)):
            print("Error: cert.pem and key.pem were not found next to WebServer.py.\n"
                  "Create a self-signed certificate with:\n"
                  '  openssl req -x509 -newkey rsa:2048 -nodes -keyout key.pem -out cert.pem -days 365 -subj "/CN=localhost"',
                  file=sys.stderr)
            sys.exit(1)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certfile=CERT_FILE, keyfile=KEY_FILE)
        Http.socket = context.wrap_socket(Http.socket, server_side=True)
        print(f"HTTPS server is running at host:{serverName}, port:{port}")
    else:
        print(f"Running regular HTTP at host:{serverName}, port:{port}")

    try:
        Http.serve_forever()
    except KeyboardInterrupt:
        print("Shutting down")
        Http.server_close()

if __name__ == '__main__':
    Active_Server()
