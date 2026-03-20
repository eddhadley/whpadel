"""Test notifications + reserved slots + time slots."""
import urllib.request, json

def api(path, body=None, token=None, method=None):
    url = f"http://localhost:4001/api{path}"
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method or ("POST" if body is not None else "GET"))
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read())

# === Notification Tests ===
print("=== Notification Tests ===")

# Register user with notifications enabled (default)
reg1 = api("/register", {"username": "alice", "email": "alice@test.com", "password": "Test123!x", "skill_level": 3, "first_name": "Alice", "last_name": "Smith", "notifications_enabled": True})
token1 = reg1["token"]
print(f"Alice registered: notifications_enabled={reg1['user'].get('notifications_enabled')}")
assert reg1["user"].get("notifications_enabled") == 1, f"Expected 1, got {reg1['user'].get('notifications_enabled')}"

# Register user with notifications disabled
reg2 = api("/register", {"username": "bob", "email": "bob@test.com", "password": "Test123!x", "skill_level": 3, "first_name": "Bob", "last_name": "Jones", "notifications_enabled": False})
token2 = reg2["token"]
print(f"Bob registered: notifications_enabled={reg2['user'].get('notifications_enabled')}")
assert reg2["user"].get("notifications_enabled") == 0, f"Expected 0, got {reg2['user'].get('notifications_enabled')}"

# Toggle Bob's notifications on
toggle = api("/me/notifications", {"notifications_enabled": True}, token2)
print(f"Bob toggled on: notifications_enabled={toggle['user']['notifications_enabled']}")
assert toggle["user"]["notifications_enabled"] == 1

# Toggle Bob's notifications off
toggle2 = api("/me/notifications", {"notifications_enabled": False}, token2)
print(f"Bob toggled off: notifications_enabled={toggle2['user']['notifications_enabled']}")
assert toggle2["user"]["notifications_enabled"] == 0

# Create a game as Alice (should trigger notification for Bob if enabled)
g = api("/games", {"court": "Court 1", "game_date": "2026-04-01", "start_time": "10:00", "min_level": 1, "max_level": 7, "reserved_slots": 0}, token1)
print(f"Game created: id={g['game']['id']}")
assert "game" in g

# Register Carol with notifications on
reg3 = api("/register", {"username": "carol", "email": "carol@test.com", "password": "Test123!x", "skill_level": 3, "first_name": "Carol", "last_name": "White", "notifications_enabled": True})
token3 = reg3["token"]

# Carol joins Alice's game (should trigger notification to Alice)
j = api(f"/games/{g['game']['id']}/join", {}, token3)
print(f"Carol joined: players={len(j['game']['players'])}")
assert len(j["game"]["players"]) == 2

# Check /api/me returns notifications_enabled
me = api("/me", token=token1)
print(f"Alice /api/me: notifications_enabled={me['user'].get('notifications_enabled')}")
assert "notifications_enabled" in me["user"]

print("\nAll notification tests passed!")
