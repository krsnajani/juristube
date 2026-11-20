import http.server
import socketserver
import urllib.parse
import json
import sqlite3
import os
import sys

from db import get_db

PORT = 8085
BASE_DIR = os.path.dirname(__file__)

class JurisTubeHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/" or path == "/index.html":
            self.serve_file(os.path.join(BASE_DIR, "templates", "index.html"), "text/html")
        elif path.startswith("/static/"):
            file_path = os.path.join(BASE_DIR, path[1:])
            if os.path.exists(file_path):
                ext = os.path.splitext(file_path)[1]
                content_type = "text/plain"
                if ext == ".css":
                    content_type = "text/css"
                elif ext == ".js":
                    content_type = "application/javascript"
                self.serve_file(file_path, content_type)
            else:
                self.send_error(404, "File Not Found")
        elif path == "/api/videos":
            self.handle_api_videos(query)
        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path.startswith("/api/video/") and path.endswith("/star"):
            parts = path.split("/")
            vid = parts[3]
            self.handle_toggle_star(vid)
        elif path.startswith("/api/video/") and path.endswith("/watched"):
            parts = path.split("/")
            vid = parts[3]
            self.handle_toggle_watched(vid)
        else:
            self.send_error(404, "Not Found")

    def serve_file(self, file_path, content_type):
        try:
            with open(file_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", f"{content_type}; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(500, f"Internal Error: {e}")

    def handle_api_videos(self, query):
        tab = query.get("tab", ["humanities"])[0]
        q = query.get("q", [""])[0].strip()
        discipline = query.get("discipline", [""])[0].strip()
        randomise = query.get("random", ["0"])[0] == "1"

        conn = get_db()
        cursor = conn.cursor()

        conditions = ["duplicate_of IS NULL"]
        params = []

        if tab == "humanities":
            conditions.append("(disciplines != '[]' OR sources LIKE '%scholar_search%' OR sources LIKE '%channel%' OR sources LIKE '%blog%')")
        elif tab == "scholars":
            conditions.append("sources LIKE '%scholar_search%'")
        elif tab == "longs":
            conditions.append("duration_sec >= 3600")
        elif tab == "starred":
            conditions.append("starred = 1")
        # 'all' has no extra condition

        if discipline:
            conditions.append("disciplines LIKE ?")
            params.append(f'%"{discipline}"%')

        if q:
            conditions.append("(title LIKE ? OR channel LIKE ? OR scholar_matches LIKE ? OR summary LIKE ?)")
            q_like = f"%{q}%"
            params.extend([q_like, q_like, q_like, q_like])

        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""

        # Weighted random: pick from top-scoring pool, shuffle within tiers
        if randomise and not q:
            order = "ORDER BY RANDOM()"
        else:
            order = "ORDER BY score DESC, duration_sec DESC"

        sql = f"SELECT * FROM videos{where_clause} {order} LIMIT 120"

        cursor.execute(sql, params)
        rows = cursor.fetchall()
        videos = [dict(r) for r in rows]
        conn.close()

        resp_data = json.dumps({"videos": videos}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(resp_data)))
        self.end_headers()
        self.wfile.write(resp_data)

    def handle_toggle_star(self, vid):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT starred FROM videos WHERE vid = ?", (vid,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            self.send_error(404, "Video not found")
            return

        new_val = 0 if row["starred"] else 1
        cursor.execute("UPDATE videos SET starred = ? WHERE vid = ?", (new_val, vid))
        conn.commit()
        conn.close()

        resp = json.dumps({"vid": vid, "starred": new_val}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(resp)

    def handle_toggle_watched(self, vid):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT watched FROM videos WHERE vid = ?", (vid,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            self.send_error(404, "Video not found")
            return

        new_val = 0 if row["watched"] else 1
        cursor.execute("UPDATE videos SET watched = ? WHERE vid = ?", (new_val, vid))
        conn.commit()
        conn.close()

        resp = json.dumps({"vid": vid, "watched": new_val}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(resp)

def run_server():
    server_address = ("", PORT)
    with socketserver.TCPServer(server_address, JurisTubeHandler) as httpd:
        print(f"=== JurisTube Server running at http://localhost:{PORT} ===")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down JurisTube server.")

if __name__ == "__main__":
    run_server()
