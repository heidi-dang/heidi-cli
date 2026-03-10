#!/usr/bin/env python3
"""Minimal OpenAI-compatible /v1/models and /v1/chat/completions server."""
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import sys

class Handler(BaseHTTPRequestHandler):
    def send_cors_headers(self):
        # Allow browser clients to call the local mock server
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def do_GET(self):
        if self.path == "/v1/models":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_cors_headers()
            self.end_headers()
            data = {"object": "list", "data": [{"id": "mistral-qlora-merged", "object": "model", "created": 1234567890, "owned_by": "local"}]}
            self.wfile.write(json.dumps(data).encode())
        elif self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
        else:
            self.send_response(404)
            self.send_cors_headers()
            self.end_headers()
    
    def do_POST(self):
        if self.path == "/v1/chat/completions":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                request_data = json.loads(body.decode())
            except:
                request_data = {}
            
            model = request_data.get("model", "mistral-qlora-merged")
            messages = request_data.get("messages", [])
            user_msg = ""
            for msg in messages:
                if msg.get("role") == "user":
                    user_msg = msg.get("content", "")
            
            response = {
                "id": "chatcmpl-mock",
                "object": "chat.completion",
                "created": 1234567890,
                "model": model,
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": f"Hello! This is a local response from {model}. You said: {user_msg[:50]}..."
                    },
                    "finish_reason": "stop"
                }],
                "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
            }
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
        else:
            print(f"[mock-server] Unsupported POST: {self.path}", file=sys.stderr)
            self.send_response(405)
            self.send_header("Content-Type", "application/json")
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Unsupported method"}).encode())

    def do_OPTIONS(self):
        # Respond to CORS preflight
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()
    
    def log_message(self, format, *args):
        print(f"[mock-server] {format % args}")

if __name__ == "__main__":
    print("Starting mock OpenAI server on 0.0.0.0:8000...")
    HTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
