import http.server
import json
import sys
import requests

ORCHESTRATOR_SIGNAL_URL = "http://ct-orchestrator:9001/internal/resume"

class GatewayHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/intent":
            # Proxy intent submissions to orchestrator (thin gateway, no business logic)
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_length) if content_length > 0 else b""

                resp = requests.post("http://ct-orchestrator:9001/intent",
                                     data=body,
                                     headers={"Content-Type": self.headers.get("Content-Type", "application/json")},
                                     timeout=5)

                self.send_response(resp.status_code)
                self.send_header("Content-Type", resp.headers.get("Content-Type", "application/json"))
                self.end_headers()
                self.wfile.write(resp.content)
                return
            except Exception as e:
                self.send_response(502)
                self.end_headers()
                self.wfile.write(f"Gateway proxy error: {str(e)}".encode())
                return

        if self.path == "/resume":
            content_length = int(self.headers['Content-Length'])
            body = self.rfile.read(content_length)
            
            try:
                data = json.loads(body)
                if data.get("ack") is True:
                    print("[GATEWAY] Valid resume signal received, signaling orchestrator...")
                    sys.stdout.flush()
                    resp = requests.post(ORCHESTRATOR_SIGNAL_URL, timeout=5)
                    
                    if resp.status_code == 200:
                        self.send_response(200)
                        self.end_headers()
                        self.wfile.write(b"Resume signal forwarded to orchestrator.")
                    else:
                        self.send_response(502)
                        self.end_headers()
                        self.wfile.write(b"Failed to signal orchestrator.")
                else:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b"Missing ack: true in payload.")
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f"Gateway error: {str(e)}".encode())
        else:
            self.send_response(404)
            self.end_headers()

if __name__ == "__main__":
    print("CT Gateway online (port 8080)")
    sys.stdout.flush()
    server = http.server.HTTPServer(("0.0.0.0", 8080), GatewayHandler)
    server.serve_forever()
