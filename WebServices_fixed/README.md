# Computer Networks: Building Web Services

Three Python programs (standard library only, Python 3.8+):

| Program | What it does | Default address |
|---|---|---|
| `WebServer(release)/WebServer.py` | HTTPS web server that hosts a resume page and supports GET, HEAD, POST, and PUT | `https://localhost:4443` (or `http://localhost:8000` with `isHTTPS = False`) |
| `WebCache(release)/WebCache.py` | Caching proxy between the client and the server; honors the server's `Cache-Control: max-age` | `http://localhost:8080` |
| `WebClient(release)/WebClient.py` | Command-line HTTP client for testing GET, HEAD, POST, and PUT | n/a |

## 1. Create a certificate (first time only)

Run this inside `WebServer(release)/`:

```bash
openssl req -x509 -newkey rsa:2048 -nodes -keyout key.pem -out cert.pem -days 365 -subj "/CN=localhost"
```

The `.pem` files are listed in `.gitignore` so the private key is never committed.

## 2. Start the server and the cache (two terminals)

```bash
python "WebServer(release)/WebServer.py"
python "WebCache(release)/WebCache.py"
```

Open `https://localhost:4443` in a browser (accept the self-signed certificate warning) to see the resume page.

## 3. Test with the client

```bash
# Directly against the server (-k allows the self-signed certificate)
python "WebClient(release)/WebClient.py" GET  https://localhost:4443/ -k
python "WebClient(release)/WebClient.py" HEAD https://localhost:4443/ -k
python "WebClient(release)/WebClient.py" POST https://localhost:4443/ '{"name": "test"}' -k
python "WebClient(release)/WebClient.py" PUT  https://localhost:4443/notes.txt 'hello' -k

# Through the cache: run GET twice and watch the cache window print MISS, then HIT
python "WebClient(release)/WebClient.py" GET http://localhost:8080/
python "WebClient(release)/WebClient.py" GET http://localhost:8080/
```

## How the cache works

- Only successful (200) `GET` responses are cached; `POST`, `PUT`, and errors always go to the server.
- Each cached entry expires after the server's `max-age` (20 seconds), then is fetched fresh.
- Cached files and `cache_metadata.json` are stored in `WebCache(release)/cache_storage/`.

To run without HTTPS, set `isHTTPS = False` in `WebServer.py` and `Origin_uses_https = False` in `WebCache.py`.
