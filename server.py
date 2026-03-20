"""
West Hants Padel Matchmaker - Web Server
Uses Python standard library http.server with custom routing.
No external dependencies required.
"""

import http.server
from http.server import ThreadingHTTPServer
import json
import os
import secrets
import urllib.parse
import re
from datetime import datetime, date

# Import our database module
import database as db
import email_service

HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", 4000))
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

# In-memory session store: {session_token: user_id}
sessions = {}

# MIME types for static file serving
MIME_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".webmanifest": "application/manifest+json",
    ".woff2": "font/woff2",
    ".woff": "font/woff",
}


def get_session_user(handler):
    """Extract user_id from Authorization header or session cookie."""
    # Check Authorization header first (Bearer token)
    auth_header = handler.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        user_id = sessions.get(token)
        if user_id:
            return db.get_user_by_id(user_id)

    # Fallback to cookie
    cookie_header = handler.headers.get("Cookie", "")
    for part in cookie_header.split(";"):
        part = part.strip()
        if part.startswith("session="):
            token = part[8:]
            user_id = sessions.get(token)
            if user_id:
                return db.get_user_by_id(user_id)
    return None


def send_json(handler, data, status=200):
    """Send a JSON response."""
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Cache-Control", "no-cache")
    handler.end_headers()
    handler.wfile.write(json.dumps(data, default=str).encode("utf-8"))


def send_error(handler, message, status=400):
    """Send a JSON error response."""
    send_json(handler, {"error": message}, status)


def read_body(handler):
    """Read and parse JSON request body."""
    content_length = int(handler.headers.get("Content-Length", 0))
    if content_length == 0:
        return {}
    body = handler.rfile.read(content_length)
    try:
        return json.loads(body.decode("utf-8"))
    except json.JSONDecodeError:
        return {}


class PadelHandler(http.server.BaseHTTPRequestHandler):
    """Custom HTTP request handler with API routing and static file serving."""

    # ─── API Routes ─────────────────────────────────────────

    def route_api(self):
        """Route API requests based on path and method."""
        path = self.path.split("?")[0]  # Remove query string
        method = self.command

        # Auth routes
        if path == "/api/register" and method == "POST":
            return self.api_register()
        if path == "/api/login" and method == "POST":
            return self.api_login()
        if path == "/api/logout" and method == "POST":
            return self.api_logout()
        if path == "/api/verify-email" and method == "POST":
            return self.api_verify_email()
        if path == "/api/resend-verification" and method == "POST":
            return self.api_resend_verification()
        if path == "/api/forgot-password" and method == "POST":
            return self.api_forgot_password()
        if path == "/api/reset-password" and method == "POST":
            return self.api_reset_password()
        if path == "/api/me" and method == "GET":
            return self.api_me()
        if path == "/api/me/skill-level" and method == "POST":
            return self.api_update_skill_level()
        if path == "/api/me/password" and method == "POST":
            return self.api_change_password()
        if path == "/api/me/name" and method == "POST":
            return self.api_update_name()
        if path == "/api/me/games" and method == "GET":
            return self.api_my_games()

        # Game routes
        if path == "/api/games" and method == "GET":
            return self.api_list_games()
        if path == "/api/games" and method == "POST":
            return self.api_create_game()

        # Game detail routes: /api/games/<id>
        match = re.match(r"^/api/games/(\d+)$", path)
        if match and method == "GET":
            return self.api_get_game(int(match.group(1)))

        # Join/leave: /api/games/<id>/join or /api/games/<id>/leave
        match = re.match(r"^/api/games/(\d+)/(join|leave)$", path)
        if match and method == "POST":
            game_id = int(match.group(1))
            action = match.group(2)
            if action == "join":
                return self.api_join_game(game_id)
            else:
                return self.api_leave_game(game_id)

        # Court availability
        if path == "/api/courts/availability" and method == "GET":
            return self.api_court_availability()

        # Skill levels reference
        if path == "/api/skill-levels" and method == "GET":
            return send_json(self, db.SKILL_LEVELS)

        # Courts reference
        if path == "/api/courts" and method == "GET":
            return send_json(self, db.COURTS)

        # Time slots reference (accepts optional ?date=YYYY-MM-DD for day-specific slots)
        if path == "/api/time-slots" and method == "GET":
            qs = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(qs)
            date_str = params.get("date", [None])[0]
            if date_str:
                return send_json(self, db.get_time_slots_for_date(date_str))
            return send_json(self, db.TIME_SLOTS_WEEKDAY)

        # Health check for Azure App Service
        if path == "/api/health" and method == "GET":
            return send_json(self, {"status": "healthy"})

        send_error(self, "Not found", 404)

    # ─── Auth endpoints ─────────────────────────────────────

    def api_register(self):
        data = read_body(self)
        try:
            user = db.register_user(
                username=data.get("username", ""),
                email=data.get("email", ""),
                password=data.get("password", ""),
                skill_level=int(data.get("skill_level", 0)),
                first_name=data.get("first_name", ""),
                last_name=data.get("last_name", ""),
            )
            # Send verification email
            code = user.pop("_verification_code", None)
            if code:
                email_service.send_verification_email(
                    user["email"], user.get("first_name", ""), code
                )
            # Create session (user can log in but is unverified)
            token = secrets.token_hex(32)
            sessions[token] = user["id"]
            self.send_response(201)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Set-Cookie", f"session={token}; Path=/; SameSite=Lax; Max-Age=86400")
            self.end_headers()
            self.wfile.write(json.dumps({"user": user, "token": token}, default=str).encode("utf-8"))
        except (ValueError, TypeError) as e:
            send_error(self, str(e))

    def api_login(self):
        data = read_body(self)
        user = db.authenticate_user(
            data.get("username", ""),
            data.get("password", "")
        )
        if user:
            # Remove password fields from response
            safe_user = {k: v for k, v in user.items() if k not in ("password_hash", "password_salt")}
            token = secrets.token_hex(32)
            sessions[token] = user["id"]
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Set-Cookie", f"session={token}; Path=/; SameSite=Lax; Max-Age=86400")
            self.end_headers()
            self.wfile.write(json.dumps({"user": safe_user, "token": token}, default=str).encode("utf-8"))
        else:
            send_error(self, "Invalid username or password", 401)

    def api_logout(self):
        cookie_header = self.headers.get("Cookie", "")
        for part in cookie_header.split(";"):
            part = part.strip()
            if part.startswith("session="):
                token = part[8:]
                sessions.pop(token, None)
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Set-Cookie", "session=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0")
        self.end_headers()
        self.wfile.write(json.dumps({"message": "Logged out"}).encode("utf-8"))

    def api_verify_email(self):
        user = get_session_user(self)
        if not user:
            return send_error(self, "Not authenticated", 401)
        data = read_body(self)
        code = data.get("code", "").strip()
        if not code:
            return send_error(self, "Verification code is required")
        try:
            updated_user = db.verify_email(user["id"], code)
            send_json(self, {"user": updated_user})
        except ValueError as e:
            send_error(self, str(e))

    def api_resend_verification(self):
        user = get_session_user(self)
        if not user:
            return send_error(self, "Not authenticated", 401)
        try:
            updated_user, code = db.resend_verification(user["id"])
            email_service.send_verification_email(
                updated_user["email"], updated_user.get("first_name", ""), code
            )
            send_json(self, {"message": "Verification email sent"})
        except ValueError as e:
            send_error(self, str(e))

    def api_forgot_password(self):
        data = read_body(self)
        identifier = data.get("identifier", "").strip()
        if not identifier:
            return send_error(self, "Please enter your username or email")
        try:
            result = db.request_password_reset(identifier)
            if result:
                user_info, code = result
                email_service.send_password_reset_email(
                    user_info["email"], user_info.get("first_name", ""), code
                )
            send_json(self, {"message": "If an account exists with that username or email, a reset code has been sent"})
        except ValueError as e:
            send_error(self, str(e))

    def api_reset_password(self):
        data = read_body(self)
        identifier = data.get("identifier", "").strip()
        code = data.get("code", "").strip()
        new_password = data.get("new_password", "")
        if not identifier or not code or not new_password:
            return send_error(self, "All fields are required")
        try:
            db.reset_password(identifier, code, new_password)
            send_json(self, {"message": "Password reset successfully. You can now sign in."})
        except ValueError as e:
            send_error(self, str(e))

    def api_me(self):
        user = get_session_user(self)
        if user:
            send_json(self, {"user": user})
        else:
            send_error(self, "Not authenticated", 401)

    def api_update_skill_level(self):
        user = get_session_user(self)
        if not user:
            return send_error(self, "Not authenticated", 401)
        data = read_body(self)
        try:
            skill_level = int(data.get("skill_level", 0))
            force = bool(data.get("force", False))
            result = db.update_user_skill_level(user["id"], skill_level, force=force)
            if "affected_games" in result:
                send_json(self, result)
            else:
                send_json(self, {"user": result["user"], "removed_from": result["removed_from"]})
        except (ValueError, TypeError) as e:
            send_error(self, str(e))

    def api_change_password(self):
        user = get_session_user(self)
        if not user:
            return send_error(self, "Not authenticated", 401)
        data = read_body(self)
        try:
            updated = db.change_password(
                user["id"],
                data.get("current_password", ""),
                data.get("new_password", ""),
            )
            send_json(self, {"user": updated})
        except (ValueError, TypeError) as e:
            send_error(self, str(e))

    def api_update_name(self):
        user = get_session_user(self)
        if not user:
            return send_error(self, "Not authenticated", 401)
        data = read_body(self)
        try:
            updated = db.update_user_name(
                user["id"],
                data.get("first_name", ""),
                data.get("last_name", ""),
            )
            send_json(self, {"user": updated})
        except (ValueError, TypeError) as e:
            send_error(self, str(e))

    def api_my_games(self):
        user = get_session_user(self)
        if not user:
            return send_error(self, "Not authenticated", 401)
        games = db.list_user_games(user["id"])
        send_json(self, {"games": games})

    # ─── Game endpoints ─────────────────────────────────────

    def api_list_games(self):
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)

        date_from = params.get("date_from", [None])[0]
        skill_level = params.get("skill_level", [None])[0]
        show_past = params.get("show_past", ["false"])[0].lower() == "true"

        games = db.list_games(date_from=date_from, skill_level=skill_level, show_past=show_past)
        send_json(self, {"games": games})

    def api_create_game(self):
        user = get_session_user(self)
        if not user:
            return send_error(self, "Not authenticated", 401)

        data = read_body(self)
        try:
            game = db.create_game(
                creator_id=user["id"],
                court=data.get("court", ""),
                game_date=data.get("game_date", ""),
                start_time=data.get("start_time", ""),
                min_level=int(data.get("min_level", 1)),
                max_level=int(data.get("max_level", 7)),
                max_players=int(data.get("max_players", 4)),
                reserved_slots=int(data.get("reserved_slots", 0)),
                notes=data.get("notes", ""),
            )
            send_json(self, {"game": game}, 201)
        except (ValueError, TypeError) as e:
            send_error(self, str(e))

    def api_get_game(self, game_id):
        game = db.get_game_by_id(game_id)
        if game:
            send_json(self, {"game": game})
        else:
            send_error(self, "Game not found", 404)

    def api_join_game(self, game_id):
        user = get_session_user(self)
        if not user:
            return send_error(self, "Not authenticated", 401)
        try:
            game = db.join_game(game_id, user["id"])
            send_json(self, {"game": game})
        except ValueError as e:
            send_error(self, str(e))

    def api_leave_game(self, game_id):
        user = get_session_user(self)
        if not user:
            return send_error(self, "Not authenticated", 401)
        try:
            result = db.leave_game(game_id, user["id"])
            send_json(self, result)
        except ValueError as e:
            send_error(self, str(e))

    def api_court_availability(self):
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        game_date = params.get("date", [date.today().isoformat()])[0]
        availability = db.get_court_availability(game_date)
        send_json(self, {"date": game_date, "availability": availability})

    # ─── Static file serving ────────────────────────────────

    def serve_static(self):
        """Serve static files from the static directory."""
        path = self.path.split("?")[0]

        # Default to index.html for SPA routing
        if path == "/" or not os.path.splitext(path)[1]:
            path = "/index.html"

        file_path = os.path.join(STATIC_DIR, path.lstrip("/"))
        file_path = os.path.normpath(file_path)

        # Security: prevent directory traversal
        if not file_path.startswith(os.path.normpath(STATIC_DIR)):
            self.send_error(403)
            return

        if os.path.isfile(file_path):
            ext = os.path.splitext(file_path)[1].lower()
            content_type = MIME_TYPES.get(ext, "application/octet-stream")

            self.send_response(200)
            self.send_header("Content-Type", content_type)

            # No caching in development; production should use a CDN/reverse proxy
            self.send_header("Cache-Control", "no-cache")

            self.end_headers()

            with open(file_path, "rb") as f:
                self.wfile.write(f.read())
        else:
            # SPA fallback: serve index.html for all unmatched routes
            index_path = os.path.join(STATIC_DIR, "index.html")
            if os.path.isfile(index_path):
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                with open(index_path, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404)

    # ─── HTTP Method Handlers ───────────────────────────────

    def do_GET(self):
        if self.path.startswith("/api/"):
            try:
                self.route_api()
            except Exception as e:
                print(f"[SERVER ERROR] {self.path}: {e}")
                send_error(self, "Internal server error", 500)
        else:
            self.serve_static()

    def do_POST(self):
        if self.path.startswith("/api/"):
            try:
                self.route_api()
            except Exception as e:
                print(f"[SERVER ERROR] {self.path}: {e}")
                send_error(self, "Internal server error", 500)
        else:
            send_error(self, "Not found", 404)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, format, *args):
        """Custom log format."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {args[0]}")


def main():
    """Start the web server."""
    print(f"""
╔══════════════════════════════════════════════════╗
║                                                  ║
║   🏸  West Hants Padel Matchmaker                ║
║                                                  ║
║   Server running on http://localhost:{PORT}        ║
║                                                  ║
║   Press Ctrl+C to stop                           ║
║                                                  ║
╚══════════════════════════════════════════════════╝
    """)

    server = ThreadingHTTPServer((HOST, PORT), PadelHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.server_close()


if __name__ == "__main__":
    main()
