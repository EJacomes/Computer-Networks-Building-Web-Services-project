import socket
import threading
import os
import time
import json
import ssl
import hashlib
import re

Server_IP = '0.0.0.0'   # address the cache listens on
Origin_IP = '127.0.0.1' # address of the origin web server (0.0.0.0 cannot be connected to on every OS)
Cache_port = 8080
Web_port_http = 8000
Web_port_https = 4443
Origin_uses_https = True  # must match isHTTPS in WebServer.py
Default_max_age = 20      # seconds, used if the origin sends no max-age

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
Cache_dir = os.path.join(BASE_DIR, "cache_storage")
metadata_file = os.path.join(Cache_dir, "cache_metadata.json")

metadata_lock = threading.Lock()

def load_metadata():
    try:
        with open(metadata_file, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_metadata(metadata):
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)

def parse_request_line(request_data):
    """Returns (method, url) from the first line of an HTTP request."""
    try:
        parts = request_data.split(b'\r\n')[0].split(b' ')
        return parts[0].upper(), parts[1]
    except IndexError:
        return None, None

def get_cache_filename(request_header):
    method, url = parse_request_line(request_header)
    if url is None:
        return None
    filename = hashlib.md5(method + b' ' + url).hexdigest()
    return os.path.join(Cache_dir, filename)

def recv_http_message(sock, is_request):
    """Reads a complete HTTP message (headers + body), not just the first 4096 bytes."""
    data = b''
    while b'\r\n\r\n' not in data:
        chunk = sock.recv(4096)
        if not chunk:
            return data
        data += chunk

    header_end = data.index(b'\r\n\r\n') + 4
    headers = data[:header_end].decode('iso-8859-1')
    match = re.search(r'(?im)^content-length:\s*(\d+)', headers)

    if match:
        total = header_end + int(match.group(1))
        while len(data) < total:
            chunk = sock.recv(4096)
            if not chunk:
                break
            data += chunk
    elif not is_request:
        # No Content-Length: the origin closes the connection when done
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            data += chunk
    return data

def get_status_code(response_data):
    try:
        return int(response_data.split(b'\r\n', 1)[0].split(b' ')[1])
    except (IndexError, ValueError):
        return None

def get_max_age(response_data):
    header_end = response_data.find(b'\r\n\r\n')
    headers = response_data[:header_end].decode('iso-8859-1')
    match = re.search(r'(?im)^cache-control:.*max-age=(\d+)', headers)
    return int(match.group(1)) if match else Default_max_age

def fetch_from_origin(client_socket, request_data):
    print("Cache: Fetching from Origin Server")

    port = Web_port_https if Origin_uses_https else Web_port_http

    try:
        with socket.create_connection((Origin_IP, port), timeout=10) as sock:
            if Origin_uses_https:
                context = ssl._create_unverified_context()  # origin uses a self-signed cert
                with context.wrap_socket(sock, server_hostname=Origin_IP) as ssock:
                    ssock.sendall(request_data)
                    origin_response = recv_http_message(ssock, is_request=False)
            else:
                sock.sendall(request_data)
                origin_response = recv_http_message(sock, is_request=False)

        save_to_cache(request_data, origin_response)
        client_socket.sendall(origin_response)
    except Exception as e:
        print(f"Cache: Error connecting to Origin: {e}")
        client_socket.sendall(b"HTTP/1.1 502 Bad Gateway\r\nContent-Length: 0\r\n\r\n")

def save_to_cache(request_data, response_data):
    method, _ = parse_request_line(request_data)
    # Only successful GET responses are cacheable; POST/PUT must always reach the server
    if method != b'GET' or get_status_code(response_data) != 200:
        print("Cache: Response not cacheable, not saved.")
        return

    filename = get_cache_filename(request_data)
    if filename:
        print(f"Cache: Caching data to {filename}")
        with open(filename, 'wb') as f:
            f.write(response_data)
        with metadata_lock:
            metadata = load_metadata()
            metadata[os.path.basename(filename)] = {
                "url": parse_request_line(request_data)[1].decode('iso-8859-1'),
                "cached_at": time.time(),
                "max_age": get_max_age(response_data),
            }
            save_metadata(metadata)

def is_fresh(filename):
    with metadata_lock:
        entry = load_metadata().get(os.path.basename(filename))
    if not entry or not os.path.exists(filename):
        return False
    return (time.time() - entry["cached_at"]) < entry["max_age"]

def handle_client(client_socket):
    try:
      request_data = recv_http_message(client_socket, is_request=True)
      if not request_data:
        return
      method, url = parse_request_line(request_data)
      print(f"Cache: Received {method.decode() if method else '?'} request for {url.decode() if url else '?'}")

      filename = get_cache_filename(request_data)

      if method == b'GET' and filename and is_fresh(filename):
          print("Cache: Cache HIT. Serving from local copy...")

          with open(filename, 'rb') as f:
              cached_content = f.read()

          client_socket.sendall(cached_content)
      else:
          if method == b'GET' and filename and os.path.exists(filename):
              print("Cache: Cached copy expired.")
          print("Cache: Cache MISS.")
          fetch_from_origin(client_socket, request_data)
    except Exception as e:
        print(f"Cache: Error handling client connection: {e}")
    finally:
        client_socket.close()

if __name__ == '__main__':
    if not os.path.exists(Cache_dir):
        os.makedirs(Cache_dir)

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((Server_IP, Cache_port))
    server.listen(5)

    print(f"Web Cache Listening on port {Cache_port}")

    try:
        while True:
            client_sock, addr = server.accept()
            print(f"Cache: Accepted connection from {addr[0]}")

            client_handler = threading.Thread(target=handle_client, args=(client_sock,), daemon=True)
            client_handler.start()
    except KeyboardInterrupt:
        print("Cache stopping.")
        server.close()
