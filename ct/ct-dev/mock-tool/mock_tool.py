from http.server import BaseHTTPRequestHandler, HTTPServer
import json, time
from jsonschema import validate, ValidationError

CONFIDENCE_THRESHOLD = 0.65

SCHEMA_PATH = "/app/ct-intent.schema.json"
try:
    with open(SCHEMA_PATH, "r") as f:
        INTENT_SCHEMA = json.load(f)
    print(f"[MOCK TOOL] Loaded schema from {SCHEMA_PATH}")
except Exception as e:
    print(f"[MOCK TOOL] Warning: Could not load schema from {SCHEMA_PATH}, using fallback. {e}")
    INTENT_SCHEMA = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "CT Tool Intent",
        "type": "object",
        "required": ["intent", "target", "confidence", "mode"],
        "properties": {
            "intent": {
                "type": "string",
                "enum": [
                    "inspect_repo",
                    "summarise_logs",
                    "analyze_code",
                    "plan_action"
                ]
            },
            "target": {"type": "string"},
            "confidence": {"type": "number"},
            "mode": {"type": "string"}
        },
        "additionalProperties": False
    }

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        try:
            payload = json.loads(body)
            validate(instance=payload, schema=INTENT_SCHEMA)

            confidence = payload.get("confidence", 0.0)
            if confidence < CONFIDENCE_THRESHOLD:
                print(
                    f"[MOCK TOOL] ⛔ REJECTED (low confidence {confidence}) "
                    f"{time.strftime('%F %T')} {payload}"
                )
                self.send_response(422)
            else:
                print(
                    f"[MOCK TOOL] ✅ ACCEPTED "
                    f"{time.strftime('%F %T')} {payload}"
                )
                self.send_response(200)

        except ValidationError as ve:
            print(
                f"[MOCK TOOL] ❌ INVALID SCHEMA "
                f"{time.strftime('%F %T')} {ve.message}"
            )
            self.send_response(400)
        except Exception as e:
            print(f"[MOCK TOOL] ❌ ERROR {e}")
            self.send_response(500)

        self.end_headers()

# Add simple GET /health for Docker healthchecks
class HealthHandler(Handler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
        else:
            self.send_response(404)
            self.end_headers()

# Run server
HTTPServer(("0.0.0.0", 9000), HealthHandler).serve_forever()
