from http.server import HTTPServer, SimpleHTTPRequestHandler
import http.server
import os
import ssl

serverName = '127.0.0.1'
serverPortHTTP = 8000 #for base HTTP
serverPortHTTPS = 4443 #for HTTPS
isHTTPS = True

#file = open('WebResume.html', 'w')

rfile = ".../resume/Resume.pdf"

WebContent = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Resume Webpage</title>
</head>
<body>
    <h1>Found below is Erick's resume:</h1>
    <embed class="pdf-container" src = "{rfile}" type="application/pdf">
</body>
</hmtl>
"""

class WebServer(SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(bytes(WebContent, "utf-8"))

    def do_POST(self):
        content_length = int(self.headers['content-length'])
        post_data = self.rfile.read(content_length)

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

        print(f"Raw Data: {post_data}")
        self.wfile.write(b"Server: POST Received")

    def do_PUT(self):
        filename = os.path.basename(self.path)

        if not filename:
            self.send_response(400, "Bad Request")
            self.end_headers()
            self.wfile.write(b"Error: Missing filename in URI path.")
            return

        content_length = self.headers.get('Content-Length')
        if not content_length:
            self.send_response(411, "Length Required")
            self.end_headers()
            return

        file_length = int(content_length)

        with open(filename, 'wb') as output_file:
            output_file.write(self.rfile.read(file_length))

        self.send_response(201, "Created")
        self.end_headers()
        self.wfile.write(f"Successfully saved tracking payload to: {filename}\n".encode('utf-8'))
        
    def end_headers(self):
        self.send_header('Cache-Control', 'public, max-age=20')

def Active_Server():
    serverAddress = (serverName, serverPortHTTPS)

    Http = http.server.HTTPServer(serverAddress, WebServer)

    if isHTTPS:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certfile='cert.pem', keyfile='key.pem')
        Http.socket = context.wrap_socket(Http.socket, server_side=True)
        print(f"HTTPS server is running at host:{serverName}, port:{serverPortHTTPS}")
    else:
        print(f"Running regular HTTP at host:{serverName}, port:{serverPortHTTP}")

    try:
        Http.serve_forever()
    except KeyboardInterrupt:
        print("Shutting down")
        Http.server_close()

if __name__ == '__main__':
    Active_Server()