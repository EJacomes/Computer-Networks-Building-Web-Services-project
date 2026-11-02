import socket
import threading
import os
import time
import json
import ssl
import hashlib

Server_IP = '0.0.0.0'
Cache_port = 8080
Web_port_http = 8000
Web_port_https = 4443

Cache_dir = "cache_storage"

metadata_file = os.path.join(Cache_dir, "cache_metadata.json")

def get_cache_filename(request_header):
    try:
        url = request_header.split(b'\r\n')[0].split(b' ')[1]
        filename = hashlib.md5(url).hexdigest()
        return os.path.join(Cache_dir, filename)
    except IndexError:
        return None

def fetch_from_origin(client_socket, request_data):
    print("Cache: Fetching from Origin Server")

    context = ssl._create_unverified_context()

    try:
        with socket.create_connection((Server_IP, Web_port_http)) as sock:
            with context.wrap_socket(sock, server_hostname=Server_IP) as ssock:
                ssock.sendall(request_data)
                origin_response = ssock.recv(4096)
                save_to_cache(request_data, origin_response)
                client_socket.sendall(origin_response)
    except Exception as e:
        print(f"Cache: Error connecting to Origin: {e}")
        client_socket.sendall(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")

def save_to_cache(request_data, response_data):
    filename = get_cache_filename(request_data)
    if filename:
        print(f"Cache: Caching data to {filename}")
        with open(filename, 'wb') as f:
            f.write(response_data)

def handle_client(client_socket):
    try:
      request_data = client_socket.recv(4096)
      if not request_data:
        return
      print(f"Cache: Received request...") 

      filename = get_cache_filename(request_data)

      if filename and os.path.exists(filename):
          print("Cache: Cache HIT. Serving from local copy...")

          with open(filename, 'rb') as f:
              cached_content = f.read()
          
          client_socket.sendall(cached_content) 
      else:
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
    server.bind(('', Cache_port))
    server.listen(5)

    print(f"Web Cache Listening on port {Cache_port}")

    try:
        while True:
            client_sock, addr = server.accept()
            print(f"Cache: Accepted connection from {addr[0]}")

            client_handler = threading.Thread(target=handle_client, args=(client_sock,))
            client_handler.start()
    except KeyboardInterrupt:
        print("Cache stopping.")
        server.close()