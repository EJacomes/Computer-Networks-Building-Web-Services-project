import urllib.request
import urllib.parse
import ssl
import json
import argparse
import sys

class Client:
    def __init__(self, insecure=False):
        #starts up the client
        self.ssl_context = None
        if insecure:
            self.ssl_context = ssl._create_unverified_context()
            print("(!) Warning: SSL verification disabled.", file=sys.stderr)
        else:
            self.ssl_context = ssl.create_default_context()

    def print_response_details(self, response, body_only=False):
        print(f"\n<- Response ({response.status} {response.reason}):")
        if not body_only:
            print("--- Headers ---")
            for header, value in response.getheaders():
                print(f"{header}: {value}")
            print("--- Body ---")

        try:
           body = response.read().decode('utf-8')

           if body_only:
              print(body)
           else:
               if 'application/json' in response.getheader('Content-Type', ''):
                   print(json.dumps(json.loads(body), indent=2))
               else:
                   print(body)
        except Exception as e:
            if not body_only:
                print(f"[Error decoding body: {e}]")

    def _make_request(self, method, url, data=None, headers=None):
        if headers is None:
            headers = {}

        data_bytes = None

        if data:
            if isinstance(data, (dict, list)):
                data_bytes = json.dumps(data).encode('utf-8')
                if 'Content-Type' not in headers:
                   headers['Content-Type'] = 'application/json'
            elif isinstance(data, str):
                data_bytes = data.encode('utf-8')

        req = urllib.request.Request(url, data=data_bytes, headers=headers, method=method)

        print(f"-> Sending {method} request to {url}...")
        if data:
            print(f"   with data: {data if isinstance(data, str) else json.dumps(data)}")

        try:
            with urllib.request.urlopen(req, context=self.ssl_context) as response:
                if method == 'HEAD':
                    self.print_response_details(response, body_only=False)
                else:
                    self.print_response_details(response, body_only=False)
        except urllib.error.HTTPError as e:
            print(f"(!) HTTP Error: {e.code} {e.reason}", file=sys.stderr)
        except urllib.error.URLError as e:
            print(f"(!) URL Error: {e.reason}", file=sys.stderr)
        except Exception as e:
            print(f"(!) Unexpected error: {e}", file=sys.stderr)

    def get(self, url, headers=None):
        self._make_request('GET', url, headers=headers)

    def head(self, url, headers=None):
        # The server must respond with HEADERS ONLY for a HEAD request.
        self._make_request('HEAD', url, headers=headers)

    def post(self, url, data, headers=None):
        self._make_request('POST', url, data=data, headers=headers)

    def put(self, url, data, headers=None):
        # A PUT request sends data to update/create a resource at a specific URL.
        self._make_request('PUT', url, data=data, headers=headers)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="A simple Python HTTP client for web service testing.")
    parser.add_argument("method", choices=['GET', 'POST', 'HEAD', 'PUT'], help="The HTTP method to use.")
    parser.add_argument("url", help="The full URL (http or https) to request.")
    parser.add_argument("data", nargs='?', help="Data for POST or PUT requests (e.g., raw string or JSON).")
    parser.add_argument("-k", "--insecure", action="store_true", help="Allow connections to HTTPS sites without valid SSL certs.")

    args = parser.parse_args()

    client = Client(insecure=args.insecure)

    processed_data = args.data
    if args.data and (args.data.startswith('{') or args.data.startswith('[')):
        try:
            processed_data = json.loads(args.data)
        except json.JSONDecodeError:
            pass

    if args.method == 'GET':
        client.get(args.url)
    elif args.method == 'HEAD':
        client.head(args.url)
    elif args.method == 'POST':
        if not processed_data:
            parser.error("Data is required for POST requests.")
        client.post(args.url, processed_data)
    elif args.method == 'PUT':
        if not processed_data:
            parser.error("Data is required for PUT requests.")
        client.put(args.url, processed_data)