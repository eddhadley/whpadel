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

# Valid time slots – hours depend on day of week
# Mon-Fri: 09:00-20:00 (last game ends 21:00)
# Sat-Sun: 09:00-17:00 (last game ends 18:00)
TIME_SLOTS_WEEKDAY = [f"{h:02d}:00" for h in range(9, 21)]
TIME_SLOTS_WEEKEND = [f"{h:02d}:00" for h in range(9, 18)]
# All possible slots (superset) for backwards-compat
TIME_SLOTS = TIME_SLOTS_WEEKDAY

def get_time_slots_for_date(date_str):
    """Return the valid time slots for a given date string (YYYY-MM-DD)."""
    from datetime import datetime
    d = datetime.strptime(date_str, "%Y-%m-%d")
    if d.weekday() >= 5:  # Saturday=5, Sunday=6
        return TIME_SLOTS_WEEKEND
    return TIME_SLOTS_WEEKDAY


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
                notify_new_games INTEGER NOT NULL DEFAULT 1,
                notify_player_joined INTEGER NOT NULL DEFAULT 1,
                notify_reminders INTEGER NOT NULL DEFAULT 1,
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
                reserved_slots INTEGER NOT NULL DEFAULT 0 CHECK(reserved_slots BETWEEN 0 AND 3),
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
        # Migrations for existing databases
        cursor = db_cursor(conn)
        cursor.execute("""
            ALTER TABLE games ADD COLUMN IF NOT EXISTS reserved_slots INTEGER NOT NULL DEFAULT 0;
            ALTER TABLE users ADD COLUMN IF NOT EXISTS notify_new_games INTEGER NOT NULL DEFAULT 1;
            ALTER TABLE users ADD COLUMN IF NOT EXISTS notify_player_joined INTEGER NOT NULL DEFAULT 1;
            ALTER TABLE users ADD COLUMN IF NOT EXISTS notify_reminders INTEGER NOT NULL DEFAULT 1;
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
                notify_new_games INTEGER NOT NULL DEFAULT 1,
                notify_player_joined INTEGER NOT NULL DEFAULT 1,
                notify_reminders INTEGER NOT NULL DEFAULT 1,
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
                reserved_slots INTEGER NOT NULL DEFAULT 0 CHECK(reserved_slots BETWEEN 0 AND 3),
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

def validate_password(password):
    """Validate password complexity: 8+ chars, letters, numbers, special characters."""
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters")
    if not any(c.isalpha() for c in password):
        raise ValueError("Password must contain at least one letter")
    if not any(c.isdigit() for c in password):
        raise ValueError("Password must contain at least one number")
    if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?/~`' for c in password):
        raise ValueError("Password must contain at least one special character")


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


def register_user(username, email, password, skill_level, first_name, last_name, notify_new_games=True, notify_player_joined=True, notify_reminders=True):
    """Register a new user with email verification. Returns user dict or raises ValueError."""
    if not username or not email or not password:
        raise ValueError("Username, email and password are required")
    if not (1 <= skill_level <= 7):
        raise ValueError("Invalid skill level")
    validate_password(password)

    password_hash, salt = hash_password(password)
    verification_code = generate_verification_code()
    from datetime import datetime, timedelta
    expires = (datetime.utcnow() + timedelta(minutes=15)).isoformat()

    conn = get_db()
    try:
        cursor = db_cursor(conn)
        ng = 1 if notify_new_games else 0
        npj = 1 if notify_player_joined else 0
        nr = 1 if notify_reminders else 0
        if USE_POSTGRES:
            cursor.execute(
                """INSERT INTO users (username, email, password_hash, password_salt, 
                   skill_level, first_name, last_name, email_verified, notify_new_games, notify_player_joined, notify_reminders, verification_code, verification_expires)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s) RETURNING id""",
                (username.strip(), email.strip().lower(), password_hash, salt,
                 skill_level, first_name.strip(), last_name.strip(),
                 ng, npj, nr, verification_code, expires)
            )
            user_id = cursor.fetchone()["id"]
        else:
            cursor.execute(
                """INSERT INTO users (username, email, password_hash, password_salt, 
                   skill_level, first_name, last_name, email_verified, notify_new_games, notify_player_joined, notify_reminders, verification_code, verification_expires)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?)""",
                (username.strip(), email.strip().lower(), password_hash, salt,
                 skill_level, first_name.strip(), last_name.strip(),
                 ng, npj, nr, verification_code, expires)
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
    Returns (user_dict, reset_code) or None if not found."""
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
            return None
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
    validate_password(new_password)

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
        _q("SELECT id, username, email, skill_level, first_name, last_name, email_verified, notify_new_games, notify_player_joined, notify_reminders, created_at FROM users WHERE id = %s"),
        (user_id,)
    )
    user = cursor.fetchone()
    if should_close:
        conn.close()
    return dict(user) if user else None


# ─── Game helpers ───────────────────────────────────────────────

def create_game(creator_id, court, game_date, start_time, min_level, max_level, max_players=4, reserved_slots=0, notes=""):
    """Create a new game. Creator auto-joins. Returns game dict."""
    if court not in COURTS:
        raise ValueError(f"Invalid court. Must be one of: {', '.join(COURTS)}")
    valid_slots = get_time_slots_for_date(game_date)
    if start_time not in valid_slots:
        if valid_slots is TIME_SLOTS_WEEKEND:
            raise ValueError("Invalid time slot. Weekend games run from 09:00 to 17:00")
        else:
            raise ValueError("Invalid time slot. Weekday games run from 09:00 to 20:00")
    if not (1 <= min_level <= 7) or not (1 <= max_level <= 7):
        raise ValueError("Invalid skill level range")
    if min_level > max_level:
        raise ValueError("Minimum level cannot be higher than maximum level")
    if not (0 <= reserved_slots <= 3):
        raise ValueError("Reserved slots must be between 0 and 3")

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

    # Check max active games limit
    if count_user_future_games(creator_id) >= MAX_ACTIVE_GAMES:
        raise ValueError(f"You can only be in {MAX_ACTIVE_GAMES} upcoming games at a time")

    conn = get_db()
    try:
        cursor = db_cursor(conn)
        if USE_POSTGRES:
            cursor.execute(
                """INSERT INTO games (creator_id, court, game_date, start_time, 
                   min_level, max_level, max_players, reserved_slots, notes)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
                (creator_id, court, game_date, start_time, min_level, max_level, max_players, reserved_slots, notes)
            )
            game_id = cursor.fetchone()["id"]
        else:
            cursor.execute(
                """INSERT INTO games (creator_id, court, game_date, start_time, 
                   min_level, max_level, max_players, reserved_slots, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (creator_id, court, game_date, start_time, min_level, max_level, max_players, reserved_slots, notes)
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

        # Check if game is full (actual players + reserved slots >= max_players)
        reserved = game.get("reserved_slots", 0)
        if len(game["players"]) + reserved >= game["max_players"]:
            raise ValueError("This game is full")

        # Check max active games limit
        if count_user_future_games(user_id, conn) >= MAX_ACTIVE_GAMES:
            raise ValueError(f"You can only be in {MAX_ACTIVE_GAMES} upcoming games at a time")

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


def remove_player_from_game(game_id, player_id, host_id):
    """Host removes a player from their game."""
    conn = get_db()
    try:
        game = get_game_by_id(game_id, conn)
        if not game:
            raise ValueError("Game not found")
        if game["creator_id"] != host_id:
            raise ValueError("Only the host can remove players")
        if player_id == host_id:
            raise ValueError("Host cannot remove themselves")
        if not any(p["id"] == player_id for p in game["players"]):
            raise ValueError("Player is not in this game")

        cursor = db_cursor(conn)
        cursor.execute(
            _q("DELETE FROM game_players WHERE game_id = %s AND user_id = %s"),
            (game_id, player_id)
        )
        conn.commit()
        return get_game_by_id(game_id, conn)
    finally:
        conn.close()


def update_reserved_slots(game_id, new_reserved_slots, host_id):
    """Host adjusts reserved slots for their game."""
    conn = get_db()
    try:
        game = get_game_by_id(game_id, conn)
        if not game:
            raise ValueError("Game not found")
        if game["creator_id"] != host_id:
            raise ValueError("Only the host can modify reserved slots")
        if not isinstance(new_reserved_slots, int) or not (0 <= new_reserved_slots <= 3):
            raise ValueError("Reserved slots must be between 0 and 3")
        if len(game["players"]) + new_reserved_slots > game["max_players"]:
            raise ValueError(f"Too many slots: {len(game['players'])} players + {new_reserved_slots} reserved exceeds {game['max_players']} max")

        cursor = db_cursor(conn)
        cursor.execute(
            _q("UPDATE games SET reserved_slots = %s WHERE id = %s"),
            (new_reserved_slots, game_id)
        )
        conn.commit()
        return get_game_by_id(game_id, conn)
    finally:
        conn.close()


def get_incompatible_games(user_id, new_level, conn=None):
    """Find future games the user is in where new_level is outside min/max range."""
    own_conn = conn is None
    if own_conn:
        conn = get_db()
    try:
        cursor = db_cursor(conn)
        query = f"""
            SELECT g.id, g.court, g.game_date, g.start_time, g.min_level, g.max_level
            FROM games g
            JOIN game_players gp ON gp.game_id = g.id
            WHERE gp.user_id = %s
              AND {_future_games_filter()}
              AND (%s < g.min_level OR %s > g.max_level)
            ORDER BY g.game_date ASC, g.start_time ASC
        """
        cursor.execute(_q(query), (user_id, new_level, new_level))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        if own_conn:
            conn.close()


def update_user_skill_level(user_id, skill_level, force=False):
    """Update a user's skill level. If force=False and there are incompatible
    games, returns {'affected_games': [...]} instead of updating.
    If force=True, updates level and removes user from incompatible games."""
    if not (1 <= skill_level <= 7):
        raise ValueError("Invalid skill level")
    conn = get_db()
    try:
        affected = get_incompatible_games(user_id, skill_level, conn)
        if affected and not force:
            level_names = {l["value"]: l["name"] for l in SKILL_LEVELS}
            for g in affected:
                g["min_level_name"] = level_names.get(g["min_level"], "?")
                g["max_level_name"] = level_names.get(g["max_level"], "?")
            return {"affected_games": affected}

        cursor = db_cursor(conn)
        # Remove from incompatible future games
        if affected:
            game_ids = [g["id"] for g in affected]
            placeholders = ",".join(["%s"] * len(game_ids))
            cursor.execute(
                _q(f"DELETE FROM game_players WHERE user_id = %s AND game_id IN ({placeholders})"),
                [user_id] + game_ids
            )

        cursor.execute(
            _q("UPDATE users SET skill_level = %s WHERE id = %s"),
            (skill_level, user_id)
        )
        if cursor.rowcount == 0:
            raise ValueError("User not found")
        conn.commit()
        return {"user": get_user_by_id(user_id, conn), "removed_from": len(affected)}
    finally:
        conn.close()


def change_password(user_id, current_password, new_password):
    """Change a user's password after verifying the current one."""
    validate_password(new_password)
    conn = get_db()
    try:
        cursor = db_cursor(conn)
        cursor.execute(
            _q("SELECT password_hash, password_salt FROM users WHERE id = %s"),
            (user_id,)
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError("User not found")
        row = dict(row)
        hashed, _ = hash_password(current_password, row["password_salt"])
        if hashed != row["password_hash"]:
            raise ValueError("Current password is incorrect")
        new_hash, new_salt = hash_password(new_password)
        cursor.execute(
            _q("UPDATE users SET password_hash = %s, password_salt = %s WHERE id = %s"),
            (new_hash, new_salt, user_id)
        )
        conn.commit()
        return get_user_by_id(user_id, conn)
    finally:
        conn.close()


def update_user_name(user_id, first_name, last_name):
    """Update a user's first and last name."""
    if not first_name or not first_name.strip():
        raise ValueError("First name is required")
    if not last_name or not last_name.strip():
        raise ValueError("Last name is required")
    conn = get_db()
    try:
        cursor = db_cursor(conn)
        cursor.execute(
            _q("UPDATE users SET first_name = %s, last_name = %s WHERE id = %s"),
            (first_name.strip(), last_name.strip(), user_id)
        )
        if cursor.rowcount == 0:
            raise ValueError("User not found")
        conn.commit()
        return get_user_by_id(user_id, conn)
    finally:
        conn.close()


MAX_ACTIVE_GAMES = 6


def count_user_future_games(user_id, conn=None):
    """Count how many future games a user is currently in."""
    own_conn = conn is None
    if own_conn:
        conn = get_db()
    try:
        cursor = db_cursor(conn)
        query = f"""
            SELECT COUNT(*) as cnt FROM game_players gp
            JOIN games g ON gp.game_id = g.id
            WHERE gp.user_id = %s AND {_future_games_filter()}
        """
        cursor.execute(_q(query), (user_id,))
        row = cursor.fetchone()
        return dict(row)["cnt"] if row else 0
    finally:
        if own_conn:
            conn.close()


def get_court_availability(date):
    """Get availability for all courts on a given date."""
    from datetime import datetime
    conn = get_db()
    cursor = db_cursor(conn)

    cursor.execute(
        _q("""SELECT g.id, g.court, g.start_time, g.min_level, g.max_level, g.max_players,
                      g.reserved_slots, g.creator_id, u.username as creator_name, u.skill_level as creator_skill,
                      (SELECT COUNT(*) FROM game_players WHERE game_id = g.id) as player_count
               FROM games g
               JOIN users u ON g.creator_id = u.id
               WHERE g.game_date = %s"""), (date,)
    )
    bookings = cursor.fetchall()
    conn.close()

    booked = {}
    for b in bookings:
        b = dict(b)
        key = f"{b['court']}_{b['start_time']}"
        booked[key] = b

    # Determine which slots are in the past for today
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    is_today = (date == today_str)
    current_hour = now.hour

    slots_for_date = get_time_slots_for_date(date)
    availability = {}
    for court in COURTS:
        availability[court] = {}
        for slot in slots_for_date:
            key = f"{court}_{slot}"
            slot_hour = int(slot.split(":")[0])
            if key in booked:
                game = booked[key]
                availability[court][slot] = {
                    "available": False,
                    "game_id": game["id"],
                    "game": {
                        "id": game["id"],
                        "creator_name": game["creator_name"],
                        "min_level": game["min_level"],
                        "max_level": game["max_level"],
                        "max_players": game["max_players"],
                        "reserved_slots": game.get("reserved_slots", 0),
                        "player_count": game["player_count"],
                    }
                }
            elif is_today and slot_hour <= current_hour:
                availability[court][slot] = {"available": False, "game_id": None, "past": True}
            else:
                availability[court][slot] = {"available": True, "game_id": None}

    return availability


# ─── Notification helpers ───────────────────────────────────────

def update_notification_preferences(user_id, notify_new_games=None, notify_player_joined=None, notify_reminders=None):
    """Update individual notification preferences. Only updates fields that are not None."""
    updates = []
    params = []
    if notify_new_games is not None:
        updates.append("notify_new_games = %s")
        params.append(1 if notify_new_games else 0)
    if notify_player_joined is not None:
        updates.append("notify_player_joined = %s")
        params.append(1 if notify_player_joined else 0)
    if notify_reminders is not None:
        updates.append("notify_reminders = %s")
        params.append(1 if notify_reminders else 0)
    if not updates:
        return get_user_by_id(user_id)
    params.append(user_id)
    conn = get_db()
    try:
        cursor = db_cursor(conn)
        cursor.execute(
            _q(f"UPDATE users SET {', '.join(updates)} WHERE id = %s"),
            params
        )
        conn.commit()
        return get_user_by_id(user_id, conn)
    finally:
        conn.close()


def get_eligible_users_for_game(game_id, exclude_user_id=None):
    """Get users with notifications enabled whose skill level is within the game's range.
    Excludes the game creator and optionally another user."""
    conn = get_db()
    try:
        cursor = db_cursor(conn)
        cursor.execute(
            _q("""SELECT u.id, u.email, u.first_name, u.skill_level
                   FROM users u
                   WHERE u.notify_new_games = 1
                     AND u.email_verified = 1
                     AND u.skill_level >= (SELECT min_level FROM games WHERE id = %s)
                     AND u.skill_level <= (SELECT max_level FROM games WHERE id = %s)
                     AND u.id != (SELECT creator_id FROM games WHERE id = %s)
            """),
            (game_id, game_id, game_id)
        )
        rows = cursor.fetchall()
        users = [dict(r) for r in rows]
        if exclude_user_id:
            users = [u for u in users if u["id"] != exclude_user_id]
        return users
    finally:
        conn.close()


def get_game_creator_info(game_id):
    """Get the game creator's notification info."""
    conn = get_db()
    try:
        cursor = db_cursor(conn)
        cursor.execute(
            _q("""SELECT u.id, u.email, u.first_name, u.notify_player_joined
                   FROM users u
                   JOIN games g ON g.creator_id = u.id
                   WHERE g.id = %s"""),
            (game_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_tomorrow_games_with_players():
    """Get all games happening tomorrow, with their players' notification info."""
    from datetime import datetime, timedelta
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    conn = get_db()
    try:
        cursor = db_cursor(conn)
        # Get tomorrow's games
        cursor.execute(
            _q("""SELECT g.id, g.court, g.game_date, g.start_time, g.max_players,
                          (SELECT COUNT(*) FROM game_players WHERE game_id = g.id) as player_count
                   FROM games g
                   WHERE g.game_date = %s"""),
            (tomorrow,)
        )
        games = [dict(r) for r in cursor.fetchall()]

        # For each game, get players with notifications enabled
        for game in games:
            cursor.execute(
                _q("""SELECT u.id, u.email, u.first_name, u.notify_reminders
                       FROM users u
                       JOIN game_players gp ON gp.user_id = u.id
                       WHERE gp.game_id = %s
                         AND u.notify_reminders = 1
                         AND u.email_verified = 1"""),
                (game["id"],)
            )
            game["notifiable_players"] = [dict(r) for r in cursor.fetchall()]

        return games
    finally:
        conn.close()


# Initialize database on import
init_db()
