import http.server
import json
import time
import os

HISTORY_FILE = "/data/ct_history.jsonl"

class ObserverHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/log":
            content_length = int(self.headers['Content-Length'])
            body = self.rfile.read(content_length)
            
            try:
                event = json.loads(body)
                event["observer_timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                
                print(f"[OBSERVER] Persisting event: {event.get('type', 'unknown')}")
                
                with open(HISTORY_FILE, "a") as f:
                    f.write(json.dumps(event) + "\n")
                
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"Logged.")
                
            except Exception as e:
                print(f"[OBSERVER] Error: {e}")
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode())
        elif self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
        else:
            self.send_response(404)
            self.end_headers()

if __name__ == "__main__":
    # Ensure data directory exists
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    
    print("CT Observer online (port 9002)")
    server = http.server.HTTPServer(("0.0.0.0", 9002), ObserverHandler)
    server.serve_forever()
