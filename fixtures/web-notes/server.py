import json, os, sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).parent
DB_PATH = Path(os.environ.get("WEB_NOTES_DB", str(ROOT / "notes.db")))
TOKEN = os.environ.get("WEB_NOTES_TOKEN", "owner-token")

def init_db():
    with sqlite3.connect(DB_PATH) as db: db.execute("create table if not exists notes (text text not null)")

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/notes":
            with sqlite3.connect(DB_PATH) as db: notes = [row[0] for row in db.execute("select text from notes")]
            self._json(200, {"notes": notes}); return
        body = (ROOT / "index.html").read_bytes(); self.send_response(200); self.send_header("Content-Type", "text/html"); self.end_headers(); self.wfile.write(body)
    def do_POST(self):
        if self.path != "/api/notes": self.send_error(404); return
        if self.headers.get("Authorization") != f"Bearer {TOKEN}": self.send_error(401); return
        size = int(self.headers.get("Content-Length", "0")); data = json.loads(self.rfile.read(size))
        with sqlite3.connect(DB_PATH) as db: db.execute("insert into notes(text) values (?)", (data["text"],))
        self._json(201, {"ok": True})
    def _json(self, status, value):
        payload = json.dumps(value).encode(); self.send_response(status); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(payload)

def serve():
    init_db(); return ThreadingHTTPServer(("127.0.0.1", 0), Handler)

if __name__ == "__main__": serve().serve_forever()
