import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse


SERVICE_NAME = "reveal-data-api"
ENVIRONMENT = os.getenv("KIPINA_ENVIRONMENT", "kipina-pilot")


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self):
        if urlparse(self.path).path != "/api/health":
            self.send_error(404)
            return

        payload = {
            "ok": True,
            "service": SERVICE_NAME,
            "environment": ENVIRONMENT,
        }
        body = (json.dumps(payload, indent=2) + "\n").encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        print("%s - - %s" % (self.address_string(), format % args), flush=True)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", 8080), Handler)
    server.serve_forever()
