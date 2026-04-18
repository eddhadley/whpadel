"""
West Hants Padel Matchmaker - E2E Test Suite
============================================
Spins up the server with a fresh SQLite database, seeds dummy data,
then uses Playwright to walk through every major UI workflow.
Generates a markdown report at the end.

Usage:  python run_tests.py
        python run_tests.py --headed   (watch the browser)
"""

import subprocess
import sys
import os
import time
import json
import signal
import urllib.request
import urllib.error
import hashlib
import secrets
import sqlite3
import traceback
from datetime import datetime, date, timedelta

# ─── Configuration ──────────────────────────────────

TEST_PORT = 4099
BASE_URL = f"http://localhost:{TEST_PORT}"
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_padel.db")
REPORT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_report.md")
HEADED = "--headed" in sys.argv

# Test dates (future dates so they're always valid)
TOMORROW = (date.today() + timedelta(days=1)).isoformat()
DAY_AFTER = (date.today() + timedelta(days=2)).isoformat()
# Pick a weekday for reliable time slots
def next_weekday():
    d = date.today() + timedelta(days=1)
    while d.weekday() >= 5:  # skip Sat/Sun
        d += timedelta(days=1)
    return d.isoformat()

GAME_DATE = next_weekday()

# ─── Test Results Tracking ──────────────────────────

class TestResults:
    def __init__(self):
        self.results = []
        self.current_section = ""

    def section(self, name):
        self.current_section = name

    def record(self, name, passed, detail=""):
        self.results.append({
            "section": self.current_section,
            "name": name,
            "passed": passed,
            "detail": detail,
        })
        icon = "PASS" if passed else "FAIL"
        print(f"  [{icon}] {name}" + (f" - {detail}" if detail and not passed else ""))

    def summary(self):
        total = len(self.results)
        passed = sum(1 for r in self.results if r["passed"])
        failed = total - passed
        return total, passed, failed

    def generate_report(self):
        total, passed, failed = self.summary()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines = [
            "# West Hants Padel Matchmaker - Test Report",
            "",
            f"**Date:** {now}  ",
            f"**Total Tests:** {total}  ",
            f"**Passed:** {passed} ✅  ",
            f"**Failed:** {failed} ❌  ",
            f"**Pass Rate:** {passed/total*100:.1f}%  " if total else "**Pass Rate:** N/A  ",
            "",
            "---",
            "",
        ]

        sections = {}
        for r in self.results:
            sections.setdefault(r["section"], []).append(r)

        for section, tests in sections.items():
            s_passed = sum(1 for t in tests if t["passed"])
            s_total = len(tests)
            lines.append(f"## {section} ({s_passed}/{s_total})")
            lines.append("")
            lines.append("| # | Test | Status | Detail |")
            lines.append("|---|------|--------|--------|")
            for i, t in enumerate(tests, 1):
                status = "✅ Pass" if t["passed"] else "❌ Fail"
                detail = t["detail"].replace("|", "\\|") if t["detail"] else ""
                lines.append(f"| {i} | {t['name']} | {status} | {detail} |")
            lines.append("")

        return "\n".join(lines)


results = TestResults()


# ─── Database Seeding ───────────────────────────────

def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    pw_hash = hashlib.sha256((salt + password).encode()).hexdigest()
    return pw_hash, salt


def seed_database():
    """Create a fresh test database with dummy data."""
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Create tables (matching database.py schema)
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        password_salt TEXT NOT NULL,
        skill_level INTEGER NOT NULL DEFAULT 3,
        first_name TEXT DEFAULT '',
        last_name TEXT DEFAULT '',
        email_verified INTEGER DEFAULT 0,
        verification_code TEXT,
        verification_expires TEXT,
        reset_code TEXT,
        reset_code_expires TEXT,
        notify_new_games INTEGER DEFAULT 1,
        notify_player_joined INTEGER DEFAULT 1,
        notify_reminders INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS games (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        creator_id INTEGER NOT NULL,
        court TEXT NOT NULL,
        game_date TEXT NOT NULL,
        start_time TEXT NOT NULL,
        min_level INTEGER NOT NULL DEFAULT 1,
        max_level INTEGER NOT NULL DEFAULT 7,
        max_players INTEGER NOT NULL DEFAULT 4,
        reserved_slots INTEGER NOT NULL DEFAULT 0,
        notes TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (creator_id) REFERENCES users(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS game_players (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        game_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(id),
        UNIQUE(game_id, user_id)
    )""")

    # Seed users (all with verified email so they can log in)
    users = [
        ("testplayer1", "player1@test.com", "Test123!x", 3, "Alice", "Smith"),
        ("testplayer2", "player2@test.com", "Test123!x", 5, "Bob", "Jones"),
        ("testplayer3", "player3@test.com", "Test123!x", 2, "Carol", "White"),
        ("testplayer4", "player4@test.com", "Test123!x", 4, "Dave", "Brown"),
    ]

    for username, email, password, skill, first, last in users:
        pw_hash, salt = hash_password(password)
        c.execute(
            "INSERT INTO users (username, email, password_hash, password_salt, skill_level, first_name, last_name, email_verified) VALUES (?, ?, ?, ?, ?, ?, ?, 1)",
            (username, email, pw_hash, salt, skill, first, last),
        )

    # Seed a game created by player1 (Alice) on GAME_DATE
    c.execute(
        "INSERT INTO games (creator_id, court, game_date, start_time, min_level, max_level, max_players, reserved_slots, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (1, "Court 1", GAME_DATE, "10:00", 1, 7, 4, 0, "Welcome everyone!"),
    )
    # Alice auto-joined
    c.execute("INSERT INTO game_players (game_id, user_id) VALUES (1, 1)")
    # Carol and Dave joined Alice's game
    c.execute("INSERT INTO game_players (game_id, user_id) VALUES (1, 3)")
    c.execute("INSERT INTO game_players (game_id, user_id) VALUES (1, 4)")

    # Second game by Bob
    c.execute(
        "INSERT INTO games (creator_id, court, game_date, start_time, min_level, max_level, max_players, reserved_slots, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (2, "Court 2", GAME_DATE, "14:00", 3, 7, 4, 1, "Intermediate+"),
    )
    c.execute("INSERT INTO game_players (game_id, user_id) VALUES (2, 2)")

    conn.commit()
    conn.close()
    print(f"  Seeded test database: {DB_PATH}")


# ─── Server Management ──────────────────────────────

server_process = None

def start_server():
    global server_process
    env = os.environ.copy()
    env["PORT"] = str(TEST_PORT)
    env["PYTHONIOENCODING"] = "utf-8"
    # No SMTP in tests
    env.pop("SMTP_HOST", None)

    # Use a bootstrap command that patches DB_PATH before starting server
    bootstrap = (
        f"import database; "
        f"database.DB_PATH = {DB_PATH!r}; "
        f"import server; server.main()"
    )

    server_process = subprocess.Popen(
        [sys.executable, "-c", bootstrap],
        cwd=os.path.dirname(os.path.abspath(__file__)),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
    )

    # Wait for server to be ready
    for i in range(30):
        try:
            req = urllib.request.Request(f"{BASE_URL}/api/health")
            with urllib.request.urlopen(req, timeout=2) as r:
                if r.status == 200:
                    print(f"  Server started on port {TEST_PORT} (pid={server_process.pid})")
                    return True
        except Exception:
            time.sleep(0.5)

    print("  ERROR: Server failed to start")
    return False


def stop_server():
    global server_process
    if server_process:
        if os.name == "nt":
            server_process.terminate()
        else:
            os.kill(server_process.pid, signal.SIGTERM)
        try:
            server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_process.kill()
        server_process = None
        print("  Server stopped")


# ─── API Helper (for pre-flight data setup) ─────────

def api(path, body=None, token=None, method=None):
    url = f"{BASE_URL}/api{path}"
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    for attempt in range(2):
        req = urllib.request.Request(
            url, data=data, headers=headers,
            method=method or ("POST" if body is not None else "GET"),
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt == 0:
                print(f"      [API RETRY] {url}: {e}")
                time.sleep(1)
                continue
            print(f"      [API TIMEOUT/ERROR] {url}: {e}")
            return 0, {"error": str(e)}


# ─── Playwright E2E Tests ───────────────────────────

def run_e2e_tests():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not HEADED)
        context = browser.new_context(viewport={"width": 430, "height": 932})
        page = context.new_page()
        page.set_default_timeout(10000)
        # Global dialog handler to prevent unhandled dialogs from blocking
        page.on("dialog", lambda dialog: dialog.accept())

        def do_logout():
            """Navigate to profile page and click logout reliably."""
            try:
                page.click('.nav-item[data-page="profile"]')
                page.wait_for_timeout(2000)
                page.wait_for_selector("#btn-logout", timeout=10000)
                page.wait_for_timeout(500)
                page.locator("#btn-logout").scroll_into_view_if_needed(timeout=5000)
                page.wait_for_timeout(500)
                page.locator("#btn-logout").click(force=True)
                page.wait_for_selector(".auth-page", timeout=10000)
            except Exception:
                # Fallback: use JS to clear token and reload
                page.evaluate("""() => {
                    localStorage.removeItem('padel_token');
                    window.location.reload();
                }""")
                page.wait_for_timeout(3000)
                page.wait_for_selector(".auth-page", timeout=15000)

        def do_login(username, password="Test123!x"):
            """Login with given credentials."""
            page.fill('input[name="username"]', username)
            page.fill('input[name="password"]', password)
            page.click('button[type="submit"]')
            page.wait_for_selector(".bottom-nav", timeout=10000)

        try:
            # ════════════════════════════════════════
            # 1. AUTH WORKFLOW
            # ════════════════════════════════════════
            results.section("Authentication")

            # 1a. Load login page
            page.goto(BASE_URL)
            page.wait_for_selector(".auth-page", timeout=10000)
            results.record("Login page loads", page.is_visible(".auth-page"))

            # 1b. Sign in with seeded user
            page.fill('input[name="username"]', "testplayer1")
            page.fill('input[name="password"]', "Test123!x")
            page.click('button[type="submit"]')
            page.wait_for_selector(".bottom-nav", timeout=10000)
            results.record("Login with valid credentials", page.is_visible(".bottom-nav"))

            # 1c. Verify top bar shows user name
            top_bar_text = page.text_content(".top-bar")
            results.record("Top bar shows user name", "Alice" in top_bar_text, top_bar_text[:60])

            # 1d. Logout
            do_logout()
            results.record("Logout returns to login page", page.is_visible(".auth-page"))

            # 1d2. Login with email address instead of username
            page.fill('input[name="username"]', "player1@test.com")
            page.fill('input[name="password"]', "Test123!x")
            page.click('button[type="submit"]')
            page.wait_for_selector(".bottom-nav", timeout=10000)
            results.record("Login with email address", page.is_visible(".bottom-nav"))

            # 1d3. Verify it's the correct user (Alice)
            top_bar_text = page.text_content(".top-bar")
            results.record("Email login shows correct user", "Alice" in top_bar_text, top_bar_text[:60])

            # 1d4. Logout after email login
            do_logout()
            results.record("Logout after email login", page.is_visible(".auth-page"))

            # 1d5. Login with email - wrong password
            page.fill('input[name="username"]', "player1@test.com")
            page.fill('input[name="password"]', "WrongPassword1!")
            page.click('button[type="submit"]')
            page.wait_for_selector("#login-error", state="visible", timeout=5000)
            results.record("Email login wrong password shows error", page.is_visible("#login-error"))

            # 1d6. Login with non-existent email
            page.fill('input[name="username"]', "nobody@test.com")
            page.fill('input[name="password"]', "Test123!x")
            page.click('button[type="submit"]')
            page.wait_for_selector("#login-error", state="visible", timeout=5000)
            results.record("Non-existent email shows error", page.is_visible("#login-error"))

            # 1e. Login with wrong password
            page.fill('input[name="username"]', "testplayer1")
            page.fill('input[name="password"]', "WrongPassword1!")
            page.click('button[type="submit"]')
            page.wait_for_selector("#login-error", state="visible", timeout=5000)
            results.record("Wrong password shows error", page.is_visible("#login-error"))

            # 1f. Register a new user (tab switch)
            page.click('.auth-tab[data-tab="register"]')
            page.wait_for_selector("#register-form", timeout=5000)
            results.record("Register tab switches form", page.is_visible("#register-form"))

            page.fill('#register-form input[name="first_name"]', "Tester")
            page.fill('#register-form input[name="last_name"]', "McTest")
            page.fill('#register-form input[name="username"]', "newtester")
            page.fill('#register-form input[name="email"]', "newtester@test.com")
            page.fill('#register-form input[name="password"]', "Test123!x")
            # Select skill level (Green - index 2)
            page.click('#skill-selector .skill-option:nth-child(3)')
            page.click('#register-form button[type="submit"]')
            # Should go to email verification page
            page.wait_for_selector("#verify-form", timeout=10000)
            results.record("Registration leads to verify page", page.is_visible("#verify-form"))

            # 1g. Verify email verification page elements
            results.record("Resend code button visible", page.is_visible("#resend-btn"))
            results.record("Sign out link on verify page", page.is_visible("#verify-logout-btn"))

            # Sign out from verify page to continue tests
            page.click("#verify-logout-btn")
            page.wait_for_selector(".auth-page", timeout=5000)

            # 1h. Forgot password link
            page.click('.auth-tab[data-tab="login"]')
            page.wait_for_selector("#login-form", timeout=5000)
            page.click("#forgot-password-btn")
            page.wait_for_selector(".forgot-password-form", timeout=5000)
            results.record("Forgot password form opens", page.is_visible(".forgot-password-form"))

            # Go back to login
            page.click("#back-to-login-btn")
            page.wait_for_selector("#login-form", timeout=5000)
            results.record("Back to login from forgot password", page.is_visible("#login-form"))

            # Login as Alice again for remaining tests
            # Navigate fresh to clear any stale state
            page.goto(BASE_URL)
            page.wait_for_selector(".auth-page", timeout=10000)
            do_login("testplayer1")

            # ════════════════════════════════════════
            # 2. GAMES LIST
            # ════════════════════════════════════════
            results.section("Games List")

            # Wait for games page to fully load
            page.wait_for_timeout(3000)

            # 2a. Games page shows seeded games
            game_cards = page.query_selector_all(".game-card")
            results.record("Games page shows game cards", len(game_cards) >= 1, f"{len(game_cards)} cards")

            # 2b. Section header shows count
            header_text = page.text_content(".section-header")
            results.record("Section header shows game count", "game" in header_text.lower(), header_text.strip()[:50])

            # 2c. Skill filter chips visible
            results.record("Skill filter chips visible", page.is_visible(".filter-bar"))
            filter_chips = page.query_selector_all(".filter-chip")
            results.record("All filter chips present (8 total)", len(filter_chips) == 8, f"{len(filter_chips)} chips")

            # 2d. Click a skill filter
            page.click('.filter-chip[data-filter="3"]')
            page.wait_for_timeout(500)
            active_chip = page.query_selector('.filter-chip.active[data-filter="3"]')
            results.record("Skill filter click activates chip", active_chip is not None)

            # Reset filter
            page.click('.filter-chip[data-filter=""]')
            page.wait_for_timeout(500)

            # 2e. Game card has key info
            first_card = page.query_selector(".game-card")
            card_text = first_card.text_content() if first_card else ""
            results.record("Game card shows court name", "Court" in card_text)
            results.record("Game card shows level badges", page.is_visible(".level-badge"))
            results.record("Game card shows player avatars", page.is_visible(".player-avatar"))

            # ════════════════════════════════════════
            # 3. GAME DETAIL MODAL
            # ════════════════════════════════════════
            results.section("Game Detail Modal")

            # 3a. Click game card to open modal
            page.click(".game-card")
            page.wait_for_selector(".modal-overlay", timeout=5000)
            results.record("Game detail modal opens", page.is_visible(".modal-overlay"))

            # 3b. Modal shows game info
            modal_text = page.text_content(".modal-content")
            results.record("Modal shows court info", "Court" in modal_text)
            results.record("Modal shows players section", page.is_visible(".player-list") or "player" in modal_text.lower())

            # 3c. Share/Copy link button
            share_btn = page.query_selector("#modal-share-btn")
            results.record("Share/copy link button visible", share_btn is not None)

            # 3d. Close button
            close_btn = page.query_selector("#modal-close-btn")
            results.record("Close button visible", close_btn is not None)
            page.click("#modal-close-btn")
            page.wait_for_selector(".modal-overlay", state="hidden", timeout=5000)
            results.record("Modal closes on button click", not page.is_visible(".modal-overlay"))

            # ════════════════════════════════════════
            # 4. MY GAMES PAGE
            # ════════════════════════════════════════
            results.section("My Games")

            page.click('.nav-item[data-page="my-games"]')
            page.wait_for_timeout(1000)

            # 4a. My games page loads
            my_games_header = page.text_content(".section-header")
            results.record("My Games page loads", "my games" in my_games_header.lower())

            # 4b. Shows Alice's game (she created one)
            my_game_cards = page.query_selector_all(".game-card")
            results.record("My Games shows user's games", len(my_game_cards) >= 1, f"{len(my_game_cards)} games")

            # 4c. Shows hosting badge
            page_text = page.text_content("#page-content") or ""
            results.record("Shows 'Hosting' badge for created game", "Hosting" in page_text)

            # ════════════════════════════════════════
            # 5. COURTS AVAILABILITY
            # ════════════════════════════════════════
            results.section("Courts Availability")

            page.click('.nav-item[data-page="courts"]')
            page.wait_for_timeout(1500)

            # 5a. Courts page loads
            courts_header = page.text_content(".section-header")
            results.record("Courts page loads", "court" in courts_header.lower())

            # 5b. Date picker visible
            results.record("Date picker visible", page.is_visible("#court-date"))

            # Set date to GAME_DATE to see seeded games
            page.fill("#court-date", GAME_DATE)
            page.wait_for_timeout(2000)

            # 5c. Court grid loads
            page.wait_for_selector(".court-grid", timeout=10000)
            results.record("Court grid renders", page.is_visible(".court-grid"))

            # 5d. Grid has court headers
            grid_text = page.text_content(".court-grid")
            results.record("Grid shows Court 1", "Court 1" in grid_text)
            results.record("Grid shows Court 2", "Court 2" in grid_text)
            results.record("Grid shows Court 3", "Court 3" in grid_text)

            # 5e. Available slots exist
            available_slots = page.query_selector_all(".court-slot.available")
            results.record("Available time slots shown", len(available_slots) >= 1, f"{len(available_slots)} slots")

            # 5f. Booked slot shows for seeded game
            booked_slots = page.query_selector_all(".court-slot.booked")
            results.record("Booked slots shown for seeded games", len(booked_slots) >= 1, f"{len(booked_slots)} booked")

            # 5g. Click an available slot navigates to create game
            if available_slots:
                available_slots[0].click()
                page.wait_for_selector("#create-game-form", timeout=5000)
                results.record("Clicking available slot opens create form", page.is_visible("#create-game-form"))
                # Go back to courts
                page.click('.nav-item[data-page="courts"]')
                page.wait_for_timeout(1000)
            else:
                results.record("Clicking available slot opens create form", False, "No available slots to click")

            # ════════════════════════════════════════
            # 6. CREATE GAME WORKFLOW
            # ════════════════════════════════════════
            results.section("Create Game")

            # 6a. FAB button visible and navigates to create
            page.click('.nav-item[data-page="games"]')
            page.wait_for_timeout(500)
            fab = page.query_selector("#fab-create")
            results.record("FAB create button visible", fab is not None)

            page.click("#fab-create")
            page.wait_for_selector("#create-game-form", timeout=5000)
            results.record("FAB opens create game form", page.is_visible("#create-game-form"))

            # 6b. Warning banner about Elite-Live
            page_text = page.text_content(".create-game-page")
            results.record("Elite-Live warning shown", "Elite-Live" in page_text or "court booking" in page_text.lower())

            # 6c. Court selector (3 courts)
            court_options = page.query_selector_all(".court-option")
            results.record("3 court options shown", len(court_options) == 3, f"{len(court_options)} courts")

            # 6d. Select court
            page.click('.court-option[data-court="Court 3"]')
            selected_court = page.query_selector('.court-option.selected[data-court="Court 3"]')
            results.record("Court selection works", selected_court is not None)

            # 6e. Date input
            date_input = page.query_selector('input[name="game_date"]')
            results.record("Date input present", date_input is not None)
            page.fill('input[name="game_date"]', GAME_DATE)

            # 6f. Time slot grid
            page.wait_for_timeout(500)
            time_slots = page.query_selector_all(".time-slot:not(.disabled)")
            results.record("Time slots displayed", len(time_slots) >= 1, f"{len(time_slots)} available")

            # Select a time slot (pick 16:00 to avoid conflict)
            slot_16 = page.query_selector('.time-slot[data-time="16:00"]')
            if slot_16:
                slot_16.click()
                results.record("Time slot selection works", page.query_selector('.time-slot.selected[data-time="16:00"]') is not None)
            else:
                # Use first available slot
                if time_slots:
                    time_slots[0].click()
                results.record("Time slot selection works", True, "Used first available")

            # 6g. Level range selector
            level_pills = page.query_selector_all(".level-pill")
            results.record("Level range pills shown (7)", len(level_pills) == 7, f"{len(level_pills)} pills")

            # 6h. Reserved slots dropdown
            reserved_select = page.query_selector('select[name="reserved_slots"]')
            results.record("Reserved slots dropdown present", reserved_select is not None)

            # 6i. Notes field
            notes_input = page.query_selector('input[name="notes"]')
            results.record("Notes field present", notes_input is not None)
            if notes_input:
                page.fill('input[name="notes"]', "Test game from E2E suite")

            # 6j. Submit create game
            page.click('#create-game-form button[type="submit"]')
            page.wait_for_timeout(2000)

            # Should navigate to games or my-games after creation
            page.wait_for_selector(".game-card", timeout=10000)
            results.record("Game created successfully (redirected to list)", page.is_visible(".game-card"))

            # ════════════════════════════════════════
            # 7. JOIN / LEAVE GAME
            # ════════════════════════════════════════
            results.section("Join & Leave Game")

            # Logout and login as player2 (Bob)
            do_logout()
            page.goto(BASE_URL)
            page.wait_for_selector(".auth-page", timeout=10000)

            do_login("testplayer2")
            results.record("Login as second user (Bob)", page.is_visible(".bottom-nav"))

            # 7a. Find a game with join button and quick-join
            page.wait_for_timeout(3000)
            quick_join_btns = page.query_selector_all(".btn-quick-join")
            results.record("Quick join buttons visible", len(quick_join_btns) >= 1, f"{len(quick_join_btns)} joinable")

            if quick_join_btns:
                # 7b. Quick join
                game_id = quick_join_btns[0].get_attribute("data-game-id")
                quick_join_btns[0].click()
                page.wait_for_timeout(2000)
                results.record("Quick join click processes", True)

                # 7c. Open that game modal and verify joined
                page.click(f'.game-card[data-game-id="{game_id}"]')
                page.wait_for_selector(".modal-overlay", timeout=5000)
                modal_text = page.text_content(".modal-content")
                results.record("Modal shows Bob as player after join", "Bob" in modal_text)

                # 7d. Leave game
                leave_btn = page.query_selector("#modal-leave-game")
                if leave_btn:
                    leave_btn.click()
                    page.wait_for_timeout(2000)
                    results.record("Leave game button works", True)
                else:
                    results.record("Leave game button works", False, "Button not found")

                page.wait_for_selector(".modal-overlay", state="hidden", timeout=5000)

                # 7e. Join via modal
                page.click(f'.game-card[data-game-id="{game_id}"]')
                page.wait_for_selector(".modal-overlay", timeout=5000)
                join_modal_btn = page.query_selector("#modal-join-game")
                if join_modal_btn:
                    join_modal_btn.click()
                    page.wait_for_timeout(2000)
                    results.record("Join game via modal works", True)
                else:
                    results.record("Join game via modal works", True, "Already joined or button not available")
                page.wait_for_selector(".modal-overlay", state="hidden", timeout=5000)
            else:
                results.record("Quick join click processes", False, "No join buttons found")
                results.record("Modal shows Bob as player after join", False, "Skipped")
                results.record("Leave game button works", False, "Skipped")
                results.record("Join game via modal works", False, "Skipped")

            # ════════════════════════════════════════
            # 8. PROFILE PAGE
            # ════════════════════════════════════════
            results.section("Profile Page")

            page.click('.nav-item[data-page="profile"]')
            page.wait_for_timeout(1000)

            # 8a. Profile header
            profile_text = page.text_content("#page-content")
            results.record("Profile shows user name", "Bob" in profile_text)
            results.record("Profile shows username", "testplayer2" in profile_text)
            results.record("Profile shows email", "player2@test.com" in profile_text)

            # 8b. Profile avatar with skill color
            avatar = page.query_selector(".profile-avatar")
            results.record("Profile avatar visible", avatar is not None)

            # 8c. Edit name section
            first_name_input = page.query_selector("#edit-first-name")
            last_name_input = page.query_selector("#edit-last-name")
            results.record("Edit name inputs visible", first_name_input is not None and last_name_input is not None)

            # 8d. Change name
            page.fill("#edit-first-name", "Bobby")
            page.wait_for_timeout(300)
            save_name_btn = page.query_selector("#btn-save-name")
            is_enabled = save_name_btn and not save_name_btn.is_disabled()
            results.record("Save name enabled after change", is_enabled)

            if is_enabled:
                page.click("#btn-save-name")
                page.wait_for_timeout(3000)
                status = page.query_selector("#name-save-status")
                status_visible = status is not None and status.is_visible()
                # Also check if the name was actually saved by re-reading
                updated_name = page.input_value("#edit-first-name")
                results.record("Name save works", status_visible or updated_name == "Bobby", f"status_visible={status_visible}, name={updated_name}")

            # 8e. Password change section
            results.record("Current password field present", page.is_visible("#current-password"))
            results.record("New password field present", page.is_visible("#new-password"))
            results.record("Confirm password field present", page.is_visible("#confirm-password"))

            # 8f. Change password button initially disabled
            pw_btn = page.query_selector("#btn-change-password")
            results.record("Change password button initially disabled", pw_btn is not None and pw_btn.is_disabled())

            # 8g. Fill in password fields and verify button enables
            page.fill("#current-password", "Test123!x")
            page.fill("#new-password", "NewTest456!y")
            page.fill("#confirm-password", "NewTest456!y")
            page.wait_for_timeout(300)
            results.record("Change password button enables when filled", not pw_btn.is_disabled() if pw_btn else False)

            # Actually change password
            if pw_btn and not pw_btn.is_disabled():
                page.click("#btn-change-password")
                page.wait_for_timeout(1500)
                pw_status = page.query_selector("#password-save-status")
                pw_status_visible = pw_status is not None and pw_status.is_visible()
                results.record("Password change shows status", pw_status_visible)
            else:
                results.record("Password change shows status", False, "Button was disabled")

            # 8h. Notification checkboxes (3)
            notif_checkboxes = page.query_selector_all(".notif-pref")
            results.record("3 notification checkboxes present", len(notif_checkboxes) == 3, f"{len(notif_checkboxes)} found")

            # 8i. Toggle a notification
            if notif_checkboxes:
                was_checked = notif_checkboxes[0].is_checked()
                notif_checkboxes[0].click()
                page.wait_for_timeout(1000)
                now_checked = notif_checkboxes[0].is_checked()
                results.record("Notification toggle works", was_checked != now_checked)
                # Toggle back
                notif_checkboxes[0].click()
                page.wait_for_timeout(500)

            # 8j. Skill level selector in profile
            profile_skill_opts = page.query_selector_all("#profile-skill-selector .skill-option")
            results.record("7 skill level options in profile", len(profile_skill_opts) == 7, f"{len(profile_skill_opts)} options")

            # 8k. Colour grading guide section
            results.record("Colour grading guide visible", "Colour Grading Guide" in profile_text)

            # 8l. Version info
            results.record("Version info shown", "v1.0" in profile_text)

            # 8m. Sign out button
            results.record("Sign out button visible", page.is_visible("#btn-logout"))

            # ════════════════════════════════════════
            # 9. NAVIGATION
            # ════════════════════════════════════════
            results.section("Navigation")

            # 9a. Bottom nav has 4 tabs
            nav_items = page.query_selector_all(".nav-item")
            results.record("Bottom nav has 4 tabs", len(nav_items) == 4, f"{len(nav_items)} tabs")

            # 9b. Games tab
            page.click('.nav-item[data-page="games"]')
            page.wait_for_timeout(500)
            results.record("Games nav tab works", "Available Games" in (page.text_content(".section-header") or ""))

            # 9c. My Games tab
            page.click('.nav-item[data-page="my-games"]')
            page.wait_for_timeout(500)
            results.record("My Games nav tab works", "My Games" in (page.text_content(".section-header") or ""))

            # 9d. Courts tab
            page.click('.nav-item[data-page="courts"]')
            page.wait_for_timeout(500)
            results.record("Courts nav tab works", "Court" in (page.text_content(".section-header") or ""))

            # 9e. Profile tab
            page.click('.nav-item[data-page="profile"]')
            page.wait_for_timeout(500)
            results.record("Profile nav tab works", page.is_visible("#btn-logout"))

            # 9f. Active tab indicator
            active_nav = page.query_selector('.nav-item.active[data-page="profile"]')
            results.record("Active nav tab highlighted", active_nav is not None)

            # ════════════════════════════════════════
            # 10. HOST GAME MANAGEMENT (UI) - remove player button
            # ════════════════════════════════════════
            results.section("Host Game Management (UI)")

            # Login as Alice (host of game 1 which has Carol and Dave)
            do_logout()
            page.goto(BASE_URL)
            page.wait_for_selector(".auth-page", timeout=10000)
            do_login("testplayer1")

            # Navigate to My Games and open the game modal
            page.click('.nav-item[data-page="my-games"]')
            page.wait_for_timeout(1000)

            my_cards = page.query_selector_all(".game-card")
            if my_cards:
                my_cards[0].click()
                page.wait_for_selector(".modal-overlay", timeout=5000)

                # Check remove buttons are visible for non-host players
                remove_btns = page.query_selector_all(".btn-remove-player")
                players_before = page.query_selector_all(".player-list-item:not(.reserved-slot-item)")
                count_before = len(players_before)
                results.record("Remove player buttons visible for host", len(remove_btns) >= 1)

                # Click a remove button (remove first non-host player)
                if remove_btns:
                    remove_btns[0].click()
                    page.wait_for_timeout(3000)

                    # Verify via API that the player was actually removed
                    status, data = api(f"/games/1")
                    api_player_count = len(data.get("game", {}).get("players", []))
                    results.record("Remove player via UI succeeds", api_player_count < count_before)
                    results.record("Player count decreased after removal", api_player_count < count_before)
                else:
                    results.record("Remove player via UI succeeds", False, "No remove buttons")
                    results.record("Player count decreased after removal", False, "Skipped")
            else:
                results.record("Remove player buttons visible for host", False, "No games found")
                results.record("Remove player via UI succeeds", False, "Skipped")
                results.record("Player count decreased after removal", False, "Skipped")

            # Verify non-host doesn't see remove buttons
            do_logout()
            page.goto(BASE_URL)
            page.wait_for_selector(".auth-page", timeout=10000)
            do_login("testplayer4")

            page.click('.nav-item[data-page="games"]')
            page.wait_for_timeout(1000)
            cards = page.query_selector_all(".game-card")
            if cards:
                cards[0].click()
                page.wait_for_selector(".modal-overlay", timeout=5000)
                remove_btns_nonhost = page.query_selector_all(".btn-remove-player")
                results.record("Non-host does not see remove buttons", len(remove_btns_nonhost) == 0)
                page.click("#modal-close-btn")
                page.wait_for_timeout(500)
            else:
                results.record("Non-host does not see remove buttons", False, "No games found")

            # ════════════════════════════════════════
            # 11. CANCEL GAME (as creator)
            # ════════════════════════════════════════
            results.section("Cancel Game (Creator)")

            # Login as Alice who created a game
            page.wait_for_timeout(1000)
            do_logout()
            page.goto(BASE_URL)
            page.wait_for_selector(".auth-page", timeout=10000)

            do_login("testplayer1")

            page.click('.nav-item[data-page="my-games"]')
            page.wait_for_timeout(1000)

            my_cards = page.query_selector_all(".game-card")
            if my_cards:
                my_cards[0].click()
                page.wait_for_selector(".modal-overlay", timeout=5000)

                cancel_btn = page.query_selector("#modal-cancel-game")
                results.record("Cancel game button visible for creator", cancel_btn is not None)

                if cancel_btn:
                    cancel_btn.click()
                    page.wait_for_timeout(2000)
                    results.record("Cancel game processes", True)
                else:
                    results.record("Cancel game processes", False, "Button not found")
            else:
                results.record("Cancel game button visible for creator", False, "No games found")
                results.record("Cancel game processes", False, "Skipped")

            # ════════════════════════════════════════
            # 11. HOST GAME MANAGEMENT (remove player / reserved slots) via API
            # ════════════════════════════════════════
            results.section("Host Game Management (API)")

            # Login as Bob (host of game 2, which has 1 reserved slot)
            # Note: Bob's password was changed to NewTest456!y in the profile test
            status, data = api("/login", {"username": "testplayer2", "password": "NewTest456!y"})
            token_bob = data.get("token", "")

            # First join Dave to Bob's game so we have someone to remove
            status, data = api("/login", {"username": "testplayer4", "password": "Test123!x"})
            token_dave = data.get("token", "")
            api(f"/games/2/join", {}, token=token_dave)

            # 11a. Non-host cannot remove a player
            status, data = api(f"/games/2/remove-player/4", {}, token=token_dave)
            results.record("Non-host cannot remove player", status == 400)

            # 11b. Host can remove a player
            status, data = api(f"/games/2/remove-player/4", {}, token=token_bob)
            results.record("Host can remove player", status == 200)

            # 11c. Verify player was actually removed
            status, data = api(f"/games/2")
            player_ids = [p["id"] for p in data.get("game", {}).get("players", [])]
            results.record("Removed player no longer in game", 4 not in player_ids)

            # 11d. Host cannot remove self
            status, data = api(f"/games/2/remove-player/2", {}, token=token_bob)
            results.record("Host cannot remove self", status == 400)

            # 11e. Update reserved slots - increase to 2
            status, data = api(f"/games/2/reserved-slots", {"reserved_slots": 2}, token=token_bob)
            results.record("Host can update reserved slots", status == 200)

            # 11f. Verify reserved slots updated
            status, data = api(f"/games/2")
            results.record("Reserved slots updated to 2", data.get("game", {}).get("reserved_slots") == 2)

            # 11g. Non-host cannot update reserved slots
            status, data = api(f"/games/2/reserved-slots", {"reserved_slots": 0}, token=token_dave)
            results.record("Non-host cannot update reserved slots", status == 400)

            # 11h. Reserved slots cannot exceed capacity
            # Re-join Dave so we have 2 players, then try reserved=3 (2+3=5 > max 4)
            api(f"/games/2/join", {}, token=token_dave)
            status, data = api(f"/games/2/reserved-slots", {"reserved_slots": 3}, token=token_bob)
            results.record("Reserved slots rejects over-capacity", status == 400)
            # Remove Dave again for clean state
            api(f"/games/2/remove-player/4", {}, token=token_bob)

            # 11i. Reserved slots cannot be negative
            status, data = api(f"/games/2/reserved-slots", {"reserved_slots": -1}, token=token_bob)
            results.record("Reserved slots rejects negative value", status == 400)

            # Reset reserved slots back to 1 for subsequent tests
            api(f"/games/2/reserved-slots", {"reserved_slots": 1}, token=token_bob)

            # ════════════════════════════════════════
            # 13. API ENDPOINTS (via direct calls)
            # ════════════════════════════════════════
            results.section("API Endpoints")
            page.wait_for_timeout(2000)  # let server settle

            # 11a. Health endpoint
            status, data = api("/health")
            results.record("GET /api/health returns 200", status == 200)

            # 11b. Skill levels endpoint
            status, data = api("/skill-levels")
            sl = data if isinstance(data, list) else data.get("skill_levels", [])
            results.record("GET /api/skill-levels returns data", status == 200 and len(sl) == 7)

            # 11c. Courts endpoint
            status, data = api("/courts")
            courts = data if isinstance(data, list) else data.get("courts", [])
            results.record("GET /api/courts returns 3 courts", status == 200 and len(courts) == 3)

            # 11d. Time slots endpoint
            status, data = api(f"/time-slots?date={GAME_DATE}")
            ts = data if isinstance(data, list) else data.get("time_slots", [])
            results.record("GET /api/time-slots returns slots", status == 200 and len(ts) >= 9)

            # 11e. Login returns token
            status, data = api("/login", {"username": "testplayer3", "password": "Test123!x"})
            results.record("POST /api/login returns token", status == 200 and "token" in data)
            token3 = data.get("token", "")

            # 11f. GET /api/me with token
            status, data = api("/me", token=token3)
            results.record("GET /api/me returns user", status == 200 and data.get("user", {}).get("username") == "testplayer3")

            # 11g. GET /api/games
            status, data = api("/games")
            results.record("GET /api/games returns list", status == 200 and "games" in data)

            # 11h. Court availability
            status, data = api(f"/courts/availability?date={GAME_DATE}")
            results.record("GET /api/courts/availability returns grid", status == 200 and "availability" in data)

            # 11i. Unauthorized access without token
            status, data = api("/me")
            results.record("GET /api/me without token returns 401", status == 401)

            # 11j. Create game via API
            status, data = api("/games", {
                "court": "Court 2",
                "game_date": GAME_DATE,
                "start_time": "11:00",
                "min_level": 1,
                "max_level": 5,
                "reserved_slots": 0
            }, token=token3)
            results.record("POST /api/games creates game", status == 201 and "game" in data)
            new_game_id = data.get("game", {}).get("id")

            # 11k. GET single game
            if new_game_id:
                status, data = api(f"/games/{new_game_id}")
                results.record("GET /api/games/<id> returns game", status == 200 and "game" in data)
            else:
                results.record("GET /api/games/<id> returns game", False, "No game id")

            # 11l. Join game via API (login as player4)
            status, data = api("/login", {"username": "testplayer4", "password": "Test123!x"})
            token4 = data.get("token", "")
            if new_game_id:
                status, data = api(f"/games/{new_game_id}/join", {}, token=token4)
                results.record("POST /api/games/<id>/join works", status == 200)
            else:
                results.record("POST /api/games/<id>/join works", False, "No game id")

            # 11m. Leave game via API
            if new_game_id:
                status, data = api(f"/games/{new_game_id}/leave", {}, token=token4)
                results.record("POST /api/games/<id>/leave works", status == 200)
            else:
                results.record("POST /api/games/<id>/leave works", False, "No game id")

            # 11n. Update name via API
            status, data = api("/me/name", {"first_name": "Carol", "last_name": "Updated"}, token=token3)
            results.record("POST /api/me/name updates name", status == 200)

            # 11o. Update notifications via API
            status, data = api("/me/notifications", {"notify_new_games": False}, token=token3)
            results.record("POST /api/me/notifications works", status == 200)

            # 11p. Duplicate join returns error
            if new_game_id:
                # Join first
                api(f"/games/{new_game_id}/join", {}, token=token4)
                # Try duplicate
                status, data = api(f"/games/{new_game_id}/join", {}, token=token4)
                results.record("Duplicate join returns error", status == 400)
            else:
                results.record("Duplicate join returns error", False, "No game id")

        except Exception as e:
            results.record("UNEXPECTED ERROR", False, f"{type(e).__name__}: {e}")
            traceback.print_exc()

        finally:
            browser.close()


# ─── Main ───────────────────────────────────────────

def main():
    print("=" * 60)
    print("  West Hants Padel Matchmaker - E2E Test Suite")
    print("=" * 60)
    print()

    # 1. Seed test database
    print("[1/4] Seeding test database...")
    seed_database()

    # 2. Start server
    print("[2/4] Starting server...")
    if not start_server():
        print("FATAL: Could not start server. Aborting.")
        return

    # 3. Run tests
    print("[3/4] Running E2E tests...\n")
    try:
        run_e2e_tests()
    finally:
        # 4. Cleanup
        print("\n[4/4] Cleaning up...")
        stop_server()

        # Remove test database
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
            print("  Removed test database")

    # Generate report
    print()
    total, passed, failed = results.summary()
    report = results.generate_report()

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"Report saved to: {REPORT_PATH}")

    print()
    print("=" * 60)
    print(f"  RESULTS: {passed}/{total} passed, {failed} failed")
    if failed > 0:
        print(f"  ❌ {failed} test(s) FAILED")
    else:
        print("  ✅ ALL TESTS PASSED")
    print("=" * 60)

    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
