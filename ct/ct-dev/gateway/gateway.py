import http.server
import json
import sys
import requests

ORCHESTRATOR_SIGNAL_URL = "http://ct-orchestrator:9001/internal/resume"

class GatewayHandler(http.server.BaseHTTPRequestHandler):
    def _unauthorized(self, msg=b"Missing or invalid Authorization header"):
        self.send_response(401)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"code": "AUTH_INVALID_KEY", "message": msg.decode() if isinstance(msg, bytes) else msg}).encode())

    def _bad_request(self, msg=b"Bad request"):
        self.send_response(400)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"code": "INVALID_REQUEST", "message": msg.decode() if isinstance(msg, bytes) else msg}).encode())

    def _proxy_get(self, target_path, headers):
        try:
            resp = requests.get(f"http://ct-orchestrator:9001{target_path}", headers=headers, timeout=5)
            self.send_response(resp.status_code)
            for k, v in resp.headers.items():
                if k.lower() == 'content-length':
                    continue
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(resp.content)
            return True
        except Exception as e:
            self.send_response(502)
            self.end_headers()
            self.wfile.write(f"Gateway proxy error: {e}".encode())
            return False

    def do_GET(self):
        # Health endpoints open
        if self.path in ("/health", "/healthz", "/readyz"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
            return

        # Proxy governance read endpoints but require auth
        if self.path.startswith("/governance/"):
            auth = self.headers.get('Authorization','')
            if not auth.startswith('Bearer '):
                return self._unauthorized()

            api_key = auth.replace('Bearer ', '')
            # Use centralized validator
            from gateway_auth import validate_request
            status_code, err = validate_request(api_key, 'GET', self.path, dict(self.headers), 0)
            if status_code != 200:
                # map to HTTP response code
                self.send_response(status_code)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"code": err or "AUTH_INVALID_KEY", "message": "Request rejected"}).encode())
                return

            # Forward to orchestrator
            return self._proxy_get(self.path, headers={'Authorization': auth})

        # Unhandled
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        if self.path == "/intent":
            # Validate auth and rate limit first
            auth = self.headers.get('Authorization','')
            if not auth.startswith('Bearer '):
                return self._unauthorized()

            api_key = auth.replace('Bearer ', '')
            from gateway_auth import validate_request
            content_length = int(self.headers.get('Content-Length', 0))
            status_code, err = validate_request(api_key, 'POST', self.path, dict(self.headers), content_length)
            if status_code != 200:
                self.send_response(status_code)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"code": err or "AUTH_INVALID_KEY", "message": "Request rejected"}).encode())
                return

            # Proxy intent submissions to orchestrator (thin gateway, no business logic)
            try:
                body_bytes = self.rfile.read(content_length) if content_length > 0 else b""
                body = json.loads(body_bytes) if body_bytes else {}

                # Normalize: map client 'target' -> orchestrator 'source' if missing
                if 'source' not in body and 'target' in body:
                    body['source'] = body['target']

                # Forward as JSON
                resp = requests.post("http://ct-orchestrator:9001/intent",
                                     json=body,
                                     headers={"Content-Type": self.headers.get("Content-Type", "application/json"), 'Authorization': auth},
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

        # POST /governance/approve/<intent_id> -- require Authorization and proxy to orchestrator
        if self.path.startswith("/governance/approve/"):
            auth = self.headers.get('Authorization','')
            print(f"[GATEWAY] approval proxy received path={self.path!r} Authorization_present={bool(auth)}")
            sys.stdout.flush()

            if not auth.startswith('Bearer '):
                return self._unauthorized()

            api_key = auth.replace('Bearer ', '')
            from gateway_auth import validate_request
            status_code, err = validate_request(api_key, 'POST', self.path, dict(self.headers), 0)
            if status_code != 200:
                self.send_response(status_code)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"code": err or "AUTH_INVALID_KEY", "message": "Request rejected"}).encode())
                return

            intent_id = self.path.split('/')[-1]
            try:
                resp = requests.post(f"http://ct-orchestrator:9001/governance/approve/{intent_id}", headers={'Authorization': auth}, timeout=10)
                print(f"[GATEWAY] proxied approval to orchestrator status={resp.status_code} body={resp.text}")
                sys.stdout.flush()

                self.send_response(resp.status_code)
                self.send_header('Content-Type', resp.headers.get('Content-Type', 'application/json'))
                self.end_headers()
                self.wfile.write(resp.content)

                # Best-effort audit
                try:
                    from audit_system import AUDIT_LOG
                    AUDIT_LOG.emit({
                        'operation': 'approval_proxied',
                        'actor': auth.replace('Bearer ', ''),
                        'result': 'proxied' if resp.status_code == 200 else 'failed',
                        'details': {'intent_id': intent_id, 'status_code': resp.status_code}
                    })
                except Exception:
                    pass

                return
            except Exception as e:
                self.send_response(502)
                self.end_headers()
                self.wfile.write(f"Gateway proxy error: {e}".encode())
                return

        if self.path == "/resume":
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length) if content_length > 0 else b""

            auth = self.headers.get('Authorization','')
            if not auth.startswith('Bearer '):
                return self._unauthorized()

            api_key = auth.replace('Bearer ', '')
            from gateway_auth import validate_request
            status_code, err = validate_request(api_key, 'POST', self.path, dict(self.headers), content_length)
            if status_code != 200:
                self.send_response(status_code)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"code": err or "AUTH_INVALID_KEY", "message": "Request rejected"}).encode())
                return

            try:
                data = json.loads(body) if body else {}
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
                    return self._bad_request(b"Missing ack: true in payload.")
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
