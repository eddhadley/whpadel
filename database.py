"""
Database module for West Hants Padel Matchmaker
Supports SQLite3 (local development) and PostgreSQL (Azure production).
Set DATABASE_URL environment variable to use PostgreSQL.
"""

import hashlib
import secrets
import os
import time

# ─── Database backend configuration ───────────────────────────────

DATABASE_URL = os.environ.get("DATABASE_URL")
USE_POSTGRES = DATABASE_URL is not None

if USE_POSTGRES:
    import psycopg2
    import psycopg2.extras
    DBIntegrityError = psycopg2.IntegrityError
else:
    import sqlite3
    DBIntegrityError = sqlite3.IntegrityError
    DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "padel.db")

# West Hants Colour Grading System (snooker ball order, lowest to highest)
SKILL_LEVELS = [
    {"name": "Red", "value": 1, "color": "#E74C3C", "label": "Red – Beginner"},
    {"name": "Yellow", "value": 2, "color": "#F1C40F", "label": "Yellow – Improver"},
    {"name": "Green", "value": 3, "color": "#27AE60", "label": "Green – Intermediate"},
    {"name": "Brown", "value": 4, "color": "#8B4513", "label": "Brown – Club Player"},
    {"name": "Blue", "value": 5, "color": "#2980B9", "label": "Blue – Advanced"},
    {"name": "Pink", "value": 6, "color": "#E91E8A", "label": "Pink – Performance"},
    {"name": "Black", "value": 7, "color": "#2C3E50", "label": "Black – Elite"},
]

COURTS = ["Court 1", "Court 2", "Court 3"]

# Valid time slots (07:00 to 21:00, 1-hour slots)
TIME_SLOTS = [f"{h:02d}:00" for h in range(7, 21)]


def get_db():
    """Get a database connection."""
    if USE_POSTGRES:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn


def db_cursor(conn):
    """Get a cursor that returns dict-like rows."""
    if USE_POSTGRES:
        return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    return conn.cursor()


def _q(sql):
    """Adapt SQL parameter placeholders for the active backend.
    Write queries with %s (PostgreSQL-style); converted to ? for SQLite."""
    if not USE_POSTGRES:
        return sql.replace('%s', '?')
    return sql


def _future_games_filter():
    """SQL fragment to filter only future games."""
    if USE_POSTGRES:
        return ("(g.game_date::date > CURRENT_DATE OR "
                "(g.game_date::date = CURRENT_DATE AND "
                "g.start_time >= to_char(CURRENT_TIMESTAMP, 'HH24:00')))")
    return ("(g.game_date > date('now', 'localtime') OR "
            "(g.game_date = date('now', 'localtime') AND "
            "g.start_time >= strftime('%H:00', 'now', 'localtime')))")


def init_db():
    """Initialize database tables."""
    conn = get_db()
    if USE_POSTGRES:
        cursor = db_cursor(conn)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                password_salt TEXT NOT NULL,
                skill_level INTEGER NOT NULL CHECK(skill_level BETWEEN 1 AND 7),
                first_name TEXT NOT NULL DEFAULT '',
                last_name TEXT NOT NULL DEFAULT '',
                email_verified INTEGER NOT NULL DEFAULT 0,
                verification_code TEXT,
                verification_expires TEXT,
                reset_code TEXT,
                reset_code_expires TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS games (
                id SERIAL PRIMARY KEY,
                creator_id INTEGER NOT NULL REFERENCES users(id),
                court TEXT NOT NULL,
                game_date TEXT NOT NULL,
                start_time TEXT NOT NULL,
                min_level INTEGER NOT NULL CHECK(min_level BETWEEN 1 AND 7),
                max_level INTEGER NOT NULL CHECK(max_level BETWEEN 1 AND 7),
                max_players INTEGER NOT NULL DEFAULT 4,
                notes TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS game_players (
                id SERIAL PRIMARY KEY,
                game_id INTEGER NOT NULL REFERENCES games(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL REFERENCES users(id),
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(game_id, user_id)
            );

            CREATE INDEX IF NOT EXISTS idx_games_date ON games(game_date, start_time);
            CREATE INDEX IF NOT EXISTS idx_games_court ON games(court, game_date, start_time);
            CREATE INDEX IF NOT EXISTS idx_game_players ON game_players(game_id, user_id);
        """)
    else:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                password_salt TEXT NOT NULL,
                skill_level INTEGER NOT NULL CHECK(skill_level BETWEEN 1 AND 7),
                first_name TEXT NOT NULL DEFAULT '',
                last_name TEXT NOT NULL DEFAULT '',
                email_verified INTEGER NOT NULL DEFAULT 0,
                verification_code TEXT,
                verification_expires TEXT,
                reset_code TEXT,
                reset_code_expires TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                creator_id INTEGER NOT NULL,
                court TEXT NOT NULL,
                game_date TEXT NOT NULL,
                start_time TEXT NOT NULL,
                min_level INTEGER NOT NULL CHECK(min_level BETWEEN 1 AND 7),
                max_level INTEGER NOT NULL CHECK(max_level BETWEEN 1 AND 7),
                max_players INTEGER NOT NULL DEFAULT 4,
                notes TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (creator_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS game_players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(game_id, user_id)
            );

            CREATE INDEX IF NOT EXISTS idx_games_date ON games(game_date, start_time);
            CREATE INDEX IF NOT EXISTS idx_games_court ON games(court, game_date, start_time);
            CREATE INDEX IF NOT EXISTS idx_game_players ON game_players(game_id, user_id);
        """)

    conn.commit()
    conn.close()


# ─── Auth helpers ───────────────────────────────────────────────

def hash_password(password, salt=None):
    """Hash a password with a random salt using SHA-256."""
    if salt is None:
        salt = secrets.token_hex(16)
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    return hashed, salt


def generate_verification_code():
    """Generate a random 6-digit verification code."""
    return f"{secrets.randbelow(900000) + 100000}"


def verify_email(user_id, code):
    """Verify a user's email with the provided code. Returns updated user dict."""
    from datetime import datetime
    conn = get_db()
    try:
        cursor = db_cursor(conn)
        cursor.execute(
            _q("SELECT verification_code, verification_expires, email_verified FROM users WHERE id = %s"),
            (user_id,)
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError("User not found")
        row = dict(row)

        if row["email_verified"]:
            raise ValueError("Email is already verified")
        if row["verification_code"] != code:
            raise ValueError("Invalid verification code")

        expires = datetime.fromisoformat(row["verification_expires"])
        if datetime.utcnow() > expires:
            raise ValueError("Verification code has expired. Please request a new one")

        cursor.execute(
            _q("UPDATE users SET email_verified = 1, verification_code = NULL, verification_expires = NULL WHERE id = %s"),
            (user_id,)
        )
        conn.commit()
        return get_user_by_id(user_id, conn)
    finally:
        conn.close()


def resend_verification(user_id):
    """Generate a new verification code for a user. Returns (user, code)."""
    from datetime import datetime, timedelta
    conn = get_db()
    try:
        cursor = db_cursor(conn)
        cursor.execute(
            _q("SELECT email_verified, email FROM users WHERE id = %s"),
            (user_id,)
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError("User not found")
        row = dict(row)

        if row["email_verified"]:
            raise ValueError("Email is already verified")

        new_code = generate_verification_code()
        expires = (datetime.utcnow() + timedelta(minutes=15)).isoformat()

        cursor.execute(
            _q("UPDATE users SET verification_code = %s, verification_expires = %s WHERE id = %s"),
            (new_code, expires, user_id)
        )
        conn.commit()
        return get_user_by_id(user_id, conn), new_code
    finally:
        conn.close()


def register_user(username, email, password, skill_level, first_name, last_name):
    """Register a new user with email verification. Returns user dict or raises ValueError."""
    if not username or not email or not password:
        raise ValueError("Username, email and password are required")
    if not (1 <= skill_level <= 7):
        raise ValueError("Invalid skill level")
    if len(password) < 6:
        raise ValueError("Password must be at least 6 characters")

    password_hash, salt = hash_password(password)
    verification_code = generate_verification_code()
    from datetime import datetime, timedelta
    expires = (datetime.utcnow() + timedelta(minutes=15)).isoformat()

    conn = get_db()
    try:
        cursor = db_cursor(conn)
        if USE_POSTGRES:
            cursor.execute(
                """INSERT INTO users (username, email, password_hash, password_salt, 
                   skill_level, first_name, last_name, email_verified, verification_code, verification_expires)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, 0, %s, %s) RETURNING id""",
                (username.strip(), email.strip().lower(), password_hash, salt,
                 skill_level, first_name.strip(), last_name.strip(),
                 verification_code, expires)
            )
            user_id = cursor.fetchone()["id"]
        else:
            cursor.execute(
                """INSERT INTO users (username, email, password_hash, password_salt, 
                   skill_level, first_name, last_name, email_verified, verification_code, verification_expires)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?)""",
                (username.strip(), email.strip().lower(), password_hash, salt,
                 skill_level, first_name.strip(), last_name.strip(),
                 verification_code, expires)
            )
            user_id = cursor.lastrowid
        conn.commit()
        user = get_user_by_id(user_id, conn)
        user["_verification_code"] = verification_code
        return user
    except DBIntegrityError as e:
        if USE_POSTGRES:
            conn.rollback()
        if "username" in str(e):
            raise ValueError("Username already taken")
        elif "email" in str(e):
            raise ValueError("Email already registered")
        else:
            raise ValueError("Registration failed")
    finally:
        conn.close()


def authenticate_user(username, password):
    """Authenticate user by username and password. Returns user dict or None."""
    conn = get_db()
    cursor = db_cursor(conn)
    cursor.execute(
        _q("SELECT * FROM users WHERE username = %s"), (username.strip(),)
    )
    user = cursor.fetchone()
    conn.close()

    if user is None:
        return None

    user = dict(user)
    hashed, _ = hash_password(password, user["password_salt"])
    if hashed == user["password_hash"]:
        return user
    return None


def request_password_reset(identifier):
    """Look up a user by username or email and generate a reset code.
    Returns (user_dict, reset_code) or raises ValueError."""
    from datetime import datetime, timedelta
    conn = get_db()
    try:
        cursor = db_cursor(conn)
        cursor.execute(
            _q("SELECT id, username, email, first_name FROM users WHERE username = %s OR email = %s"),
            (identifier.strip(), identifier.strip().lower())
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError("No account found with that username or email")
        row = dict(row)

        code = generate_verification_code()
        expires = (datetime.utcnow() + timedelta(minutes=15)).isoformat()

        cursor.execute(
            _q("UPDATE users SET reset_code = %s, reset_code_expires = %s WHERE id = %s"),
            (code, expires, row["id"])
        )
        conn.commit()
        return row, code
    finally:
        conn.close()


def reset_password(identifier, code, new_password):
    """Reset a user's password using a reset code. Returns updated user dict."""
    from datetime import datetime
    if len(new_password) < 6:
        raise ValueError("Password must be at least 6 characters")

    conn = get_db()
    try:
        cursor = db_cursor(conn)
        cursor.execute(
            _q("SELECT id, reset_code, reset_code_expires FROM users WHERE username = %s OR email = %s"),
            (identifier.strip(), identifier.strip().lower())
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError("No account found with that username or email")
        row = dict(row)

        if not row["reset_code"]:
            raise ValueError("No password reset was requested")
        if row["reset_code"] != code:
            raise ValueError("Invalid reset code")

        expires = datetime.fromisoformat(row["reset_code_expires"])
        if datetime.utcnow() > expires:
            raise ValueError("Reset code has expired. Please request a new one")

        password_hash, salt = hash_password(new_password)
        cursor.execute(
            _q("UPDATE users SET password_hash = %s, password_salt = %s, reset_code = NULL, reset_code_expires = NULL WHERE id = %s"),
            (password_hash, salt, row["id"])
        )
        conn.commit()
        return get_user_by_id(row["id"], conn)
    finally:
        conn.close()


def get_user_by_id(user_id, conn=None):
    """Get a user by their ID."""
    should_close = conn is None
    if conn is None:
        conn = get_db()
    cursor = db_cursor(conn)
    cursor.execute(
        _q("SELECT id, username, email, skill_level, first_name, last_name, email_verified, created_at FROM users WHERE id = %s"),
        (user_id,)
    )
    user = cursor.fetchone()
    if should_close:
        conn.close()
    return dict(user) if user else None


# ─── Game helpers ───────────────────────────────────────────────

def create_game(creator_id, court, game_date, start_time, min_level, max_level, max_players=4, notes=""):
    """Create a new game. Creator auto-joins. Returns game dict."""
    if court not in COURTS:
        raise ValueError(f"Invalid court. Must be one of: {', '.join(COURTS)}")
    if start_time not in TIME_SLOTS:
        raise ValueError(f"Invalid time slot. Games run hourly from 07:00 to 20:00")
    if not (1 <= min_level <= 7) or not (1 <= max_level <= 7):
        raise ValueError("Invalid skill level range")
    if min_level > max_level:
        raise ValueError("Minimum level cannot be higher than maximum level")
    if not (2 <= max_players <= 4):
        raise ValueError("Max players must be between 2 and 4")

    # Prevent booking in the past
    from datetime import datetime
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    current_hour = now.hour
    slot_hour = int(start_time.split(":")[0])
    if game_date < today_str:
        raise ValueError("Cannot create a game in the past")
    if game_date == today_str and slot_hour <= current_hour:
        raise ValueError("Cannot create a game for a time that has already passed")

    # Check court availability
    if is_court_booked(court, game_date, start_time):
        raise ValueError(f"{court} is already booked at {start_time} on {game_date}")

    # Check creator's skill level
    creator = get_user_by_id(creator_id)
    if not creator:
        raise ValueError("User not found")

    conn = get_db()
    try:
        cursor = db_cursor(conn)
        if USE_POSTGRES:
            cursor.execute(
                """INSERT INTO games (creator_id, court, game_date, start_time, 
                   min_level, max_level, max_players, notes)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
                (creator_id, court, game_date, start_time, min_level, max_level, max_players, notes)
            )
            game_id = cursor.fetchone()["id"]
        else:
            cursor.execute(
                """INSERT INTO games (creator_id, court, game_date, start_time, 
                   min_level, max_level, max_players, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (creator_id, court, game_date, start_time, min_level, max_level, max_players, notes)
            )
            game_id = cursor.lastrowid
        # Auto-join the creator
        cursor.execute(
            _q("INSERT INTO game_players (game_id, user_id) VALUES (%s, %s)"),
            (game_id, creator_id)
        )
        conn.commit()
        return get_game_by_id(game_id, conn)
    except DBIntegrityError:
        if USE_POSTGRES:
            conn.rollback()
        raise ValueError("Could not create game")
    finally:
        conn.close()


def is_court_booked(court, game_date, start_time, exclude_game_id=None):
    """Check if a court is already booked at a given date/time."""
    conn = get_db()
    cursor = db_cursor(conn)
    if exclude_game_id:
        cursor.execute(
            _q("SELECT COUNT(*) as cnt FROM games WHERE court = %s AND game_date = %s AND start_time = %s AND id != %s"),
            (court, game_date, start_time, exclude_game_id)
        )
    else:
        cursor.execute(
            _q("SELECT COUNT(*) as cnt FROM games WHERE court = %s AND game_date = %s AND start_time = %s"),
            (court, game_date, start_time)
        )
    result = cursor.fetchone()
    conn.close()
    return dict(result)["cnt"] > 0


def get_game_by_id(game_id, conn=None):
    """Get a game with its players."""
    should_close = conn is None
    if conn is None:
        conn = get_db()
    cursor = db_cursor(conn)

    cursor.execute(_q("""
        SELECT g.*, u.username as creator_name, u.skill_level as creator_skill
        FROM games g
        JOIN users u ON g.creator_id = u.id
        WHERE g.id = %s
    """), (game_id,))
    game = cursor.fetchone()

    if game is None:
        if should_close:
            conn.close()
        return None

    game_dict = dict(game)

    # Get players
    cursor.execute(_q("""
        SELECT u.id, u.username, u.first_name, u.last_name, u.skill_level, gp.joined_at
        FROM game_players gp
        JOIN users u ON gp.user_id = u.id
        WHERE gp.game_id = %s
        ORDER BY gp.joined_at ASC
    """), (game_id,))
    game_dict["players"] = [dict(p) for p in cursor.fetchall()]

    if should_close:
        conn.close()
    return game_dict


def list_games(date_from=None, skill_level=None, show_past=False):
    """List games in chronological order with optional filters."""
    conn = get_db()
    cursor = db_cursor(conn)

    query = """
        SELECT g.*, u.username as creator_name, u.skill_level as creator_skill,
               (SELECT COUNT(*) FROM game_players WHERE game_id = g.id) as player_count
        FROM games g
        JOIN users u ON g.creator_id = u.id
        WHERE 1=1
    """
    params = []

    if not show_past:
        query += f" AND {_future_games_filter()}"

    if date_from:
        query += _q(" AND g.game_date >= %s")
        params.append(date_from)

    if skill_level:
        query += _q(" AND g.min_level <= %s AND g.max_level >= %s")
        params.append(int(skill_level))
        params.append(int(skill_level))

    query += " ORDER BY g.game_date ASC, g.start_time ASC"

    cursor.execute(query, params)
    games = [dict(g) for g in cursor.fetchall()]

    # Get players for each game
    for game in games:
        cursor.execute(_q("""
            SELECT u.id, u.username, u.first_name, u.last_name, u.skill_level, gp.joined_at
            FROM game_players gp
            JOIN users u ON gp.user_id = u.id
            WHERE gp.game_id = %s
            ORDER BY gp.joined_at ASC
        """), (game["id"],))
        game["players"] = [dict(p) for p in cursor.fetchall()]

    conn.close()
    return games


def list_user_games(user_id):
    """List upcoming games that a user is hosting or has joined."""
    conn = get_db()
    cursor = db_cursor(conn)

    query = f"""
        SELECT g.*, u.username as creator_name, u.skill_level as creator_skill,
               (SELECT COUNT(*) FROM game_players WHERE game_id = g.id) as player_count
        FROM games g
        JOIN users u ON g.creator_id = u.id
        JOIN game_players gp ON gp.game_id = g.id
        WHERE gp.user_id = %s
          AND {_future_games_filter()}
        ORDER BY g.game_date ASC, g.start_time ASC
    """

    cursor.execute(_q(query), (user_id,))
    games = [dict(g) for g in cursor.fetchall()]

    for game in games:
        cursor.execute(_q("""
            SELECT u.id, u.username, u.first_name, u.last_name, u.skill_level, gp.joined_at
            FROM game_players gp
            JOIN users u ON gp.user_id = u.id
            WHERE gp.game_id = %s
            ORDER BY gp.joined_at ASC
        """), (game["id"],))
        game["players"] = [dict(p) for p in cursor.fetchall()]

    conn.close()
    return games


def join_game(game_id, user_id):
    """Join an existing game. Returns updated game dict."""
    conn = get_db()
    try:
        game = get_game_by_id(game_id, conn)
        if not game:
            raise ValueError("Game not found")

        user = get_user_by_id(user_id, conn)
        if not user:
            raise ValueError("User not found")

        # Check if already joined
        for player in game["players"]:
            if player["id"] == user_id:
                raise ValueError("You have already joined this game")

        # Check if game is full
        if len(game["players"]) >= game["max_players"]:
            raise ValueError("This game is full")

        # Check skill level
        if user["skill_level"] < game["min_level"] or user["skill_level"] > game["max_level"]:
            level_names = {l["value"]: l["name"] for l in SKILL_LEVELS}
            raise ValueError(
                f"Your skill level ({level_names[user['skill_level']]}) is outside the "
                f"required range ({level_names[game['min_level']]} – {level_names[game['max_level']]})"
            )

        cursor = db_cursor(conn)
        cursor.execute(
            _q("INSERT INTO game_players (game_id, user_id) VALUES (%s, %s)"),
            (game_id, user_id)
        )
        conn.commit()
        return get_game_by_id(game_id, conn)
    except DBIntegrityError:
        if USE_POSTGRES:
            conn.rollback()
        raise ValueError("You have already joined this game")
    finally:
        conn.close()


def leave_game(game_id, user_id):
    """Leave a game. If creator leaves, delete the game."""
    conn = get_db()
    try:
        game = get_game_by_id(game_id, conn)
        if not game:
            raise ValueError("Game not found")

        cursor = db_cursor(conn)

        if game["creator_id"] == user_id:
            # Creator is cancelling the game
            cursor.execute(_q("DELETE FROM game_players WHERE game_id = %s"), (game_id,))
            cursor.execute(_q("DELETE FROM games WHERE id = %s"), (game_id,))
            conn.commit()
            return {"deleted": True, "message": "Game cancelled"}
        else:
            cursor.execute(
                _q("DELETE FROM game_players WHERE game_id = %s AND user_id = %s"),
                (game_id, user_id)
            )
            if cursor.rowcount == 0:
                raise ValueError("You are not in this game")
            conn.commit()
            return get_game_by_id(game_id, conn)
    finally:
        conn.close()


def update_user_skill_level(user_id, skill_level):
    """Update a user's skill level. Returns updated user dict."""
    if not (1 <= skill_level <= 7):
        raise ValueError("Invalid skill level")
    conn = get_db()
    try:
        cursor = db_cursor(conn)
        cursor.execute(
            _q("UPDATE users SET skill_level = %s WHERE id = %s"),
            (skill_level, user_id)
        )
        if cursor.rowcount == 0:
            raise ValueError("User not found")
        conn.commit()
        return get_user_by_id(user_id, conn)
    finally:
        conn.close()


def get_court_availability(date):
    """Get availability for all courts on a given date."""
    from datetime import datetime
    conn = get_db()
    cursor = db_cursor(conn)

    cursor.execute(
        _q("SELECT court, start_time, id FROM games WHERE game_date = %s"), (date,)
    )
    bookings = cursor.fetchall()
    conn.close()

    booked = {}
    for b in bookings:
        b = dict(b)
        key = f"{b['court']}_{b['start_time']}"
        booked[key] = b["id"]

    # Determine which slots are in the past for today
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    is_today = (date == today_str)
    current_hour = now.hour

    availability = {}
    for court in COURTS:
        availability[court] = {}
        for slot in TIME_SLOTS:
            key = f"{court}_{slot}"
            slot_hour = int(slot.split(":")[0])
            if key in booked:
                availability[court][slot] = {"available": False, "game_id": booked[key]}
            elif is_today and slot_hour <= current_hour:
                availability[court][slot] = {"available": False, "game_id": None, "past": True}
            else:
                availability[court][slot] = {"available": True, "game_id": None}

    return availability


# Initialize database on import
init_db()
