/**
 * West Hants Padel Matchmaker - Frontend Application
 * Single-page PWA with no external JS dependencies
 */

// ═══════════════════════════════════════════════════
// State Management
// ═══════════════════════════════════════════════════

const state = {
    user: null,
    games: [],
    myGames: [],
    currentPage: 'games',    // games | my-games | create | courts | profile
    selectedGame: null,
    skillFilter: null,
    createForm: {
        court: null,
        game_date: todayISO(),
        start_time: null,
        min_level: 1,
        max_level: 7,
        reserved_slots: 0,
        notes: ''
    },
    courtDate: todayISO(),
    courtAvailability: null,
};

const SKILL_LEVELS = [
    { name: "Red", value: 1, color: "#E74C3C", label: "Beginner",
      technique: "All basic strokes need developing",
      tactical: "Working on getting ball 'Over and In'",
      movement: "Struggle to read flight of ball and get in position",
      pace: "Slow" },
    { name: "Yellow", value: 2, color: "#F1C40F", label: "Improver",
      technique: "Basic swings in place, but need developing",
      tactical: "Getting ball 'Over and In', starting to Move Opponent",
      movement: "Understand position on court. Struggle to read flight of ball consistently",
      pace: "Slow to Steady" },
    { name: "Green", value: 3, color: "#27AE60", label: "Intermediate",
      technique: "Basic swings in place, starting to understand spin",
      tactical: "Over and In, Moving Opponent, starting to Target Weaknesses",
      movement: "Better position at baseline and net. May still struggle to get to some balls",
      pace: "Steady to Medium" },
    { name: "Brown", value: 4, color: "#8B4513", label: "Club Player",
      technique: "Basic swings established. Can demonstrate spin on some shots",
      tactical: "More consistently able to get ball 'Over and In', Move Opponent and Target Weaknesses",
      movement: "Good positioning and able to get into position on more balls",
      pace: "Medium. Forehand and serve starting to develop more power" },
    { name: "Blue", value: 5, color: "#2980B9", label: "Advanced",
      technique: "Most swings solid and using spin",
      tactical: "Developing Strengths, able to Move Opponent and Target Weaknesses",
      movement: "Strong and fast or good reader of ball for better positioning on each shot",
      pace: "Medium/Fast" },
    { name: "Pink", value: 6, color: "#E91E8A", label: "Performance",
      technique: "All swings solid and using spin where appropriate",
      tactical: "All tactical areas solid",
      movement: "Very good position to ball through combination of good movement and reading of game",
      pace: "Medium/Fast to Fast" },
    { name: "Black", value: 7, color: "#2C3E50", label: "Elite",
      technique: "Technically solid",
      tactical: "Tactically solid and able to vary tactics according to opponent",
      movement: "Rarely out of position on a shot",
      pace: "Fast" },
];

const COURTS = ["Court 1", "Court 2", "Court 3"];
const TIME_SLOTS_WEEKDAY = [];
for (let h = 9; h < 21; h++) TIME_SLOTS_WEEKDAY.push(`${String(h).padStart(2,'0')}:00`);
const TIME_SLOTS_WEEKEND = [];
for (let h = 9; h < 18; h++) TIME_SLOTS_WEEKEND.push(`${String(h).padStart(2,'0')}:00`);
const TIME_SLOTS = TIME_SLOTS_WEEKDAY; // default

function getTimeSlotsForDate(dateStr) {
    if (!dateStr) return TIME_SLOTS_WEEKDAY;
    const d = new Date(dateStr + 'T12:00:00');
    const day = d.getDay(); // 0=Sun, 6=Sat
    return (day === 0 || day === 6) ? TIME_SLOTS_WEEKEND : TIME_SLOTS_WEEKDAY;
}

// ═══════════════════════════════════════════════════
// Utility Functions
// ═══════════════════════════════════════════════════

function todayISO() {
    return new Date().toISOString().split('T')[0];
}

function getSkillLevel(value) {
    return SKILL_LEVELS.find(l => l.value === value) || SKILL_LEVELS[0];
}

function formatDate(dateStr) {
    const d = new Date(dateStr + 'T12:00:00');
    const today = new Date();
    const tomorrow = new Date(today);
    tomorrow.setDate(today.getDate() + 1);

    if (dateStr === todayISO()) return 'Today';
    if (dateStr === tomorrow.toISOString().split('T')[0]) return 'Tomorrow';

    return d.toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short' });
}

function formatTime(timeStr) {
    return timeStr;
}

function endTime(startTime) {
    const h = parseInt(startTime.split(':')[0]) + 1;
    return `${String(h).padStart(2, '0')}:00`;
}

function getInitials(user) {
    if (user.first_name && user.last_name) {
        return (user.first_name[0] + user.last_name[0]).toUpperCase();
    }
    return user.username.substring(0, 2).toUpperCase();
}

function $(selector) {
    return document.querySelector(selector);
}

function $$(selector) {
    return document.querySelectorAll(selector);
}

// ═══════════════════════════════════════════════════
// API Functions
// ═══════════════════════════════════════════════════

function getToken() {
    return localStorage.getItem('padel_token');
}

function setToken(token) {
    if (token) {
        localStorage.setItem('padel_token', token);
    } else {
        localStorage.removeItem('padel_token');
    }
}

async function api(path, options = {}) {
    const headers = { 'Content-Type': 'application/json' };
    const token = getToken();
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    const config = {
        headers,
        credentials: 'same-origin',
        ...options,
        // Ensure our headers aren't overwritten by spread
        headers: { ...headers, ...(options.headers || {}) },
    };
    if (config.body && typeof config.body === 'object') {
        config.body = JSON.stringify(config.body);
    }
    try {
        const res = await fetch(`/api${path}`, config);
        const data = await res.json();
        if (!res.ok) {
            throw new Error(data.error || 'Something went wrong');
        }
        return data;
    } catch (err) {
        if (err.message === 'Failed to fetch') {
            throw new Error('Network error. Please check your connection.');
        }
        throw err;
    }
}

async function checkAuth() {
    try {
        const data = await api('/me');
        state.user = data.user;
        return true;
    } catch {
        state.user = null;
        return false;
    }
}

async function login(username, password) {
    const data = await api('/login', {
        method: 'POST',
        body: { username, password }
    });
    state.user = data.user;
    if (data.token) setToken(data.token);
    return data.user;
}

async function register(formData) {
    const data = await api('/register', {
        method: 'POST',
        body: formData
    });
    state.user = data.user;
    if (data.token) setToken(data.token);
    return data.user;
}

async function verifyEmail(code) {
    const data = await api('/verify-email', {
        method: 'POST',
        body: { code }
    });
    state.user = data.user;
    return data.user;
}

async function resendVerification() {
    await api('/resend-verification', { method: 'POST' });
}

async function forgotPassword(identifier) {
    await api('/forgot-password', {
        method: 'POST',
        body: { identifier }
    });
}

async function resetPassword(identifier, code, newPassword) {
    const data = await api('/reset-password', {
        method: 'POST',
        body: { identifier, code, new_password: newPassword }
    });
    return data;
}

async function changePassword(currentPassword, newPassword) {
    const data = await api('/me/password', {
        method: 'POST',
        body: { current_password: currentPassword, new_password: newPassword }
    });
    state.user = data.user;
    return data.user;
}

async function updateName(firstName, lastName) {
    const data = await api('/me/name', {
        method: 'POST',
        body: { first_name: firstName, last_name: lastName }
    });
    state.user = data.user;
    return data.user;
}

function validatePassword(password) {
    if (password.length < 8) return 'Password must be at least 8 characters';
    if (!/[a-zA-Z]/.test(password)) return 'Password must contain at least one letter';
    if (!/[0-9]/.test(password)) return 'Password must contain at least one number';
    if (!/[!@#$%^&*()_+\-=\[\]{}|;:,.<>?/~`]/.test(password)) return 'Password must contain at least one special character';
    return null;
}

async function logout() {
    await api('/logout', { method: 'POST' });
    state.user = null;
    setToken(null);
}

async function fetchGames() {
    const params = new URLSearchParams();
    if (state.skillFilter) params.set('skill_level', state.skillFilter);
    const data = await api(`/games?${params}`);
    state.games = data.games;
    return data.games;
}

async function fetchMyGames() {
    const data = await api('/me/games');
    state.myGames = data.games;
    return data.games;
}

async function fetchGame(id) {
    const data = await api(`/games/${id}`);
    return data.game;
}

async function createGame(gameData) {
    const data = await api('/games', {
        method: 'POST',
        body: gameData
    });
    return data.game;
}

async function joinGame(id) {
    const data = await api(`/games/${id}/join`, { method: 'POST' });
    return data.game;
}

async function leaveGame(id) {
    const data = await api(`/games/${id}/leave`, { method: 'POST' });
    return data;
}

async function fetchCourtAvailability(date) {
    const data = await api(`/courts/availability?date=${date}`);
    return data;
}

async function updateSkillLevel(skillLevel, force = false) {
    const data = await api('/me/skill-level', {
        method: 'POST',
        body: { skill_level: skillLevel, force }
    });
    if (data.affected_games) {
        return { affected_games: data.affected_games };
    }
    state.user = data.user;
    return { user: data.user, removed_from: data.removed_from || 0 };
}

// ═══════════════════════════════════════════════════
// Toast Notifications
// ═══════════════════════════════════════════════════

function showToast(message, type = 'info') {
    let container = $('.toast-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
    }
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

// ═══════════════════════════════════════════════════
// Rendering Functions
// ═══════════════════════════════════════════════════

function render() {
    const app = $('#app');
    if (!state.user) {
        app.innerHTML = renderAuthPage();
        bindAuthEvents();
    } else if (!state.user.email_verified) {
        app.innerHTML = renderVerifyEmailPage();
        bindVerifyEvents();
    } else {
        app.innerHTML = renderMainApp();
        bindMainEvents();
        // Load page content
        navigateTo(state.currentPage);
    }
}

// ─── Auth Page ──────────────────────────────────────

function renderAuthPage() {
    return `
        <div class="auth-page fade-in">
            <div class="auth-logo">
                <div class="logo-icon">🏸</div>
                <h1>West Hants Padel</h1>
                <p>Find your perfect match</p>
            </div>
            <div class="auth-card">
                <div class="auth-tabs">
                    <button class="auth-tab active" data-tab="login">Sign In</button>
                    <button class="auth-tab" data-tab="register">Register</button>
                </div>
                <div id="auth-content">
                    ${renderLoginForm()}
                </div>
            </div>
        </div>
    `;
}

function renderLoginForm() {
    return `
        <form id="login-form">
            <div class="form-group">
                <label>Username</label>
                <input type="text" class="form-input" name="username" placeholder="Enter your username" required autocomplete="username">
            </div>
            <div class="form-group">
                <label>Password</label>
                <input type="password" class="form-input" name="password" placeholder="Enter your password" required autocomplete="current-password">
            </div>
            <div id="login-error" class="form-error mb-8" style="display:none"></div>
            <button type="submit" class="btn btn-primary btn-block mt-8">Sign In</button>
        </form>
        <div style="text-align:center; margin-top:12px;">
            <button id="forgot-password-btn" class="btn btn-text" style="font-size:13px;">Forgot password?</button>
        </div>
    `;
}

function renderRegisterForm() {
    return `
        <form id="register-form">
            <div class="form-row">
                <div class="form-group">
                    <label>First Name</label>
                    <input type="text" class="form-input" name="first_name" placeholder="First" required>
                </div>
                <div class="form-group">
                    <label>Last Name</label>
                    <input type="text" class="form-input" name="last_name" placeholder="Last" required>
                </div>
            </div>
            <div class="form-group">
                <label>Username</label>
                <input type="text" class="form-input" name="username" placeholder="Choose a username" required autocomplete="username">
            </div>
            <div class="form-group">
                <label>Email</label>
                <input type="email" class="form-input" name="email" placeholder="your@email.com" required>
            </div>
            <div class="form-group">
                <label>Password</label>
                <input type="password" class="form-input" name="password" placeholder="Min 8 characters, letters + numbers + special" required minlength="8" autocomplete="new-password">
                <div class="password-requirements" style="font-size:0.75rem;color:var(--text-secondary);margin-top:4px">
                    Must be 8+ characters with letters, numbers and special characters
                </div>
            </div>
            <div class="form-group">
                <label>Skill Level <span style="font-weight:400;text-transform:none;letter-spacing:0">(West Hants Colour Grading)</span></label>
                <div class="skill-selector" id="skill-selector">
                    ${SKILL_LEVELS.map(level => `
                        <div class="skill-option" data-value="${level.value}">
                            <div class="color-swatch" style="background:${level.color}"></div>
                            <div>
                                <div class="skill-name">${level.name}</div>
                                <div class="skill-desc">${level.label}</div>
                            </div>
                        </div>
                    `).join('')}
                </div>
                <input type="hidden" name="skill_level" id="skill-level-input" value="" required>
            </div>
            <div id="register-error" class="form-error mb-8" style="display:none"></div>
            <button type="submit" class="btn btn-primary btn-block mt-8">Create Account</button>
        </form>
    `;
}

function renderVerifyEmailPage() {
    const email = state.user ? state.user.email : '';
    const masked = email ? email.replace(/^(.{2})(.*)(@.*)$/, (_, a, b, c) => a + '*'.repeat(b.length) + c) : '';
    return `
        <div class="auth-page fade-in">
            <div class="auth-logo">
                <div class="logo-icon">📧</div>
                <h1>Verify Your Email</h1>
                <p>We sent a 6-digit code to <strong>${masked}</strong></p>
            </div>
            <div class="auth-card">
                <form id="verify-form">
                    <div class="form-group">
                        <label>Verification Code</label>
                        <input type="text" class="form-input verify-code-input" name="code"
                               placeholder="000000" required maxlength="6" pattern="[0-9]{6}"
                               inputmode="numeric" autocomplete="one-time-code"
                               style="text-align:center; font-size:24px; letter-spacing:8px; font-weight:700">
                    </div>
                    <div id="verify-error" class="form-error mb-8" style="display:none"></div>
                    <button type="submit" class="btn btn-primary btn-block mt-8">Verify Email</button>
                </form>
                <div style="text-align:center; margin-top:16px;">
                    <p style="color:#666; font-size:14px; margin-bottom:8px;">Didn't receive the email?</p>
                    <button id="resend-btn" class="btn btn-outline" style="font-size:14px;">Resend Code</button>
                </div>
                <div style="text-align:center; margin-top:16px;">
                    <button id="verify-logout-btn" class="btn btn-text" style="font-size:13px; color:#999;">Sign out</button>
                </div>
            </div>
        </div>
    `;
}

// ─── Main App Layout ────────────────────────────────

function renderMainApp() {
    const level = getSkillLevel(state.user.skill_level);
    return `
        <div class="top-bar">
            <div class="top-bar-content">
                <div>
                    <h1>🏸 West Hants Padel</h1>
                    <div class="club-name">The West Hants Club</div>
                </div>
                <div class="top-bar-actions">
                    <div class="user-badge">
                        <span class="level-dot" style="background:${level.color}"></span>
                        ${state.user.first_name || state.user.username}
                    </div>
                </div>
            </div>
        </div>

        <div class="main-content" id="page-content">
            <!-- Page content rendered here -->
        </div>

        <button class="fab" id="fab-create" title="Create Game">+</button>

        <nav class="bottom-nav">
            <button class="nav-item active" data-page="games">
                <span class="nav-icon">📋</span>
                Games
            </button>
            <button class="nav-item" data-page="my-games">
                <span class="nav-icon">⭐</span>
                My Games
            </button>
            <button class="nav-item" data-page="courts">
                <span class="nav-icon">🏟️</span>
                Courts
            </button>
            <button class="nav-item" data-page="profile">
                <span class="nav-icon">👤</span>
                Profile
            </button>
        </nav>
    `;
}

// ─── Games List Page ────────────────────────────────

function renderGamesPage() {
    return `
        <div class="fade-in">
            <div class="section-header">
                <div>
                    <h2>Available Games</h2>
                    <div class="subtitle">${state.games.length} game${state.games.length !== 1 ? 's' : ''} available</div>
                </div>
            </div>

            <div class="filter-bar" id="skill-filters">
                <button class="filter-chip ${!state.skillFilter ? 'active' : ''}" data-filter="">
                    All Levels
                </button>
                ${SKILL_LEVELS.map(l => `
                    <button class="filter-chip ${state.skillFilter == l.value ? 'active' : ''}" data-filter="${l.value}">
                        <span class="chip-dot" style="background:${l.color}"></span>
                        ${l.name}
                    </button>
                `).join('')}
            </div>

            <div id="games-list">
                ${state.games.length === 0 ? renderEmptyGames() : state.games.map(renderGameCard).join('')}
            </div>
        </div>
    `;
}

function renderEmptyGames() {
    return `
        <div class="empty-state">
            <div class="icon">🏸</div>
            <h3>No games available</h3>
            <p>${state.skillFilter ? 'Try a different skill level filter or ' : ''}Be the first to create a game!</p>
            <button class="btn btn-primary" onclick="navigateTo('create')">+ Create Game</button>
        </div>
    `;
}

function renderMyGamesPage() {
    return `
        <div class="fade-in">
            <div class="section-header">
                <div>
                    <h2>My Games</h2>
                    <div class="subtitle">${state.myGames.length} upcoming game${state.myGames.length !== 1 ? 's' : ''}</div>
                </div>
            </div>

            <div id="my-games-list">
                ${state.myGames.length === 0 ? `
                    <div class="empty-state">
                        <div class="icon">📅</div>
                        <h3>No upcoming games</h3>
                        <p>Join a game or create your own!</p>
                        <button class="btn btn-primary" onclick="navigateTo('games')">Browse Games</button>
                    </div>
                ` : state.myGames.map(game => {
                    const isCreator = game.creator_id === state.user.id;
                    return `<div class="my-game-badge ${isCreator ? 'hosting' : ''}">${isCreator ? '👑 Hosting' : '✓ Joined'}</div>` + renderGameCard(game);
                }).join('')}
            </div>
        </div>
    `;
}

function renderGameCard(game) {
    const playerCount = game.players ? game.players.length : game.player_count || 0;
    const maxPlayers = game.max_players || 4;
    const reserved = game.reserved_slots || 0;
    const isFull = playerCount + reserved >= maxPlayers;
    const isJoined = game.players && state.user && game.players.some(p => p.id === state.user.id);
    const minLevel = getSkillLevel(game.min_level);
    const maxLevel = getSkillLevel(game.max_level);

    const avatars = [];
    if (game.players) {
        game.players.forEach(p => {
            const pl = getSkillLevel(p.skill_level);
            avatars.push(`<div class="player-avatar" style="background:${pl.color}" title="${p.username} (${pl.name})">${getInitials(p)}</div>`);
        });
    }
    // Reserved slots
    for (let i = 0; i < reserved; i++) {
        avatars.push(`<div class="player-avatar reserved-slot" title="Reserved by host">R</div>`);
    }
    // Open slots
    for (let i = playerCount + reserved; i < maxPlayers; i++) {
        avatars.push(`<div class="player-avatar empty-slot">+</div>`);
    }

    let actionBtn = '';
    if (isJoined) {
        actionBtn = `<span class="btn btn-sm btn-success" style="cursor:default; pointer-events: none;">✓ Joined</span>`;
    } else if (isFull) {
        actionBtn = `<span class="btn btn-sm btn-secondary" style="cursor:default; opacity:0.5">Full</span>`;
    } else {
        actionBtn = `<button class="btn btn-sm btn-primary btn-quick-join" data-game-id="${game.id}">Join</button>`;
    }

    return `
        <div class="game-card" data-game-id="${game.id}">
            <div class="game-card-header">
                <span class="game-card-court">${game.court}</span>
                <div class="game-card-time">
                    <div class="date">${formatDate(game.game_date)}</div>
                    <div class="time">${formatTime(game.start_time)} – ${endTime(game.start_time)}</div>
                </div>
            </div>
            <div class="game-card-body">
                <div class="game-card-levels">
                    Levels:
                    <span class="level-badge" style="background:${minLevel.color}">${minLevel.name}</span>
                    ${game.min_level !== game.max_level ? `
                        <span>→</span>
                        <span class="level-badge" style="background:${maxLevel.color}">${maxLevel.name}</span>
                    ` : ''}
                </div>
                <div class="game-card-players">
                    <div class="player-avatars">${avatars.join('')}</div>
                </div>
            </div>
            <div class="game-card-footer">
                <span class="player-count">${playerCount + reserved}/${maxPlayers} players${reserved ? ` (${reserved} reserved)` : ''}</span>
                ${actionBtn}
            </div>
        </div>
    `;
}

// ─── Game Detail Modal ──────────────────────────────

function renderGameModal(game) {
    const minLevel = getSkillLevel(game.min_level);
    const maxLevel = getSkillLevel(game.max_level);
    const isCreator = state.user && game.creator_id === state.user.id;
    const isJoined = game.players && state.user && game.players.some(p => p.id === state.user.id);
    const reserved = game.reserved_slots || 0;
    const isFull = game.players && game.players.length + reserved >= game.max_players;

    // Check if user's level is in range
    const userLevel = state.user ? state.user.skill_level : 0;
    const levelInRange = userLevel >= game.min_level && userLevel <= game.max_level;

    let actionButton = '';
    if (isCreator) {
        actionButton = `<button class="btn btn-danger btn-block mt-16" id="modal-cancel-game" data-game-id="${game.id}">Cancel Game</button>`;
    } else if (isJoined) {
        actionButton = `<button class="btn btn-secondary btn-block mt-16" id="modal-leave-game" data-game-id="${game.id}">Leave Game</button>`;
    } else if (isFull) {
        actionButton = `<button class="btn btn-secondary btn-block mt-16" disabled>Game is Full</button>`;
    } else if (!levelInRange) {
        actionButton = `<button class="btn btn-secondary btn-block mt-16" disabled>Your level doesn't match (${getSkillLevel(userLevel).name})</button>`;
    } else {
        actionButton = `<button class="btn btn-primary btn-block mt-16" id="modal-join-game" data-game-id="${game.id}">Join Game</button>`;
    }

    return `
        <div class="modal-overlay" id="game-modal">
            <div class="modal-content">
                <div class="modal-handle"></div>
                <div class="modal-header">
                    <h2>${game.court} — Padel Match</h2>
                </div>
                <div class="modal-body">
                    <div class="info-row">
                        <span class="info-icon">📅</span>
                        <div>
                            <div class="info-label">Date</div>
                            <div class="info-value">${formatDate(game.game_date)} (${game.game_date})</div>
                        </div>
                    </div>
                    <div class="info-row">
                        <span class="info-icon">⏰</span>
                        <div>
                            <div class="info-label">Time</div>
                            <div class="info-value">${formatTime(game.start_time)} – ${endTime(game.start_time)} (1 hour)</div>
                        </div>
                    </div>
                    <div class="info-row">
                        <span class="info-icon">🏟️</span>
                        <div>
                            <div class="info-label">Court</div>
                            <div class="info-value">${game.court}</div>
                        </div>
                    </div>
                    <div class="info-row">
                        <span class="info-icon">🎯</span>
                        <div>
                            <div class="info-label">Skill Level Required</div>
                            <div class="info-value" style="display:flex;align-items:center;gap:6px;">
                                <span class="level-badge" style="background:${minLevel.color};padding:2px 8px;border-radius:10px;font-size:0.75rem;color:white;font-weight:600">${minLevel.name}</span>
                                ${game.min_level !== game.max_level ? `
                                    <span style="color:var(--text-light)">to</span>
                                    <span class="level-badge" style="background:${maxLevel.color};padding:2px 8px;border-radius:10px;font-size:0.75rem;color:white;font-weight:600">${maxLevel.name}</span>
                                ` : ''}
                            </div>
                        </div>
                    </div>
                    ${game.notes ? `
                    <div class="info-row">
                        <span class="info-icon">📝</span>
                        <div>
                            <div class="info-label">Notes</div>
                            <div class="info-value">${escapeHtml(game.notes)}</div>
                        </div>
                    </div>
                    ` : ''}

                    <h3 style="margin-top:20px;margin-bottom:10px;font-size:1rem;font-weight:700;">
                        Players (${game.players.length + reserved}/${game.max_players})${reserved ? ` · ${reserved} reserved` : ''}
                    </h3>
                    <ul class="player-list">
                        ${game.players.map(p => {
                            const pl = getSkillLevel(p.skill_level);
                            return `
                                <li class="player-list-item">
                                    <div class="player-list-avatar" style="background:${pl.color}">${getInitials(p)}</div>
                                    <div class="player-list-info">
                                        <div class="name">
                                            ${escapeHtml(p.first_name || '')} ${escapeHtml(p.last_name || '')}
                                            ${p.id === game.creator_id ? '<span class="creator-tag">HOST</span>' : ''}
                                        </div>
                                        <div class="level">@${escapeHtml(p.username)} · <span style="color:${pl.color};font-weight:600">${pl.name}</span> (${pl.label})</div>
                                    </div>
                                </li>
                            `;
                        }).join('')}
                        ${Array.from({length: reserved}, (_, i) => `
                            <li class="player-list-item">
                                <div class="player-list-avatar reserved-slot" style="background:#9b59b6;color:white">R</div>
                                <div class="player-list-info">
                                    <div class="name">${escapeHtml(game.creator_name || 'Host')}'s guest <span class="reserved-tag">RESERVED</span></div>
                                    <div class="level">Pre-arranged player</div>
                                </div>
                            </li>
                        `).join('')}
                        ${Array.from({length: game.max_players - game.players.length - reserved}, (_, i) => `
                            <li class="player-list-item" style="opacity:0.4">
                                <div class="player-list-avatar" style="background:var(--border);color:var(--text-light)">?</div>
                                <div class="player-list-info">
                                    <div class="name">Waiting for player...</div>
                                    <div class="level">Open slot</div>
                                </div>
                            </li>
                        `).join('')}
                    </ul>

                    ${actionButton}
                    <button class="btn btn-secondary btn-block mt-8" id="modal-close-btn">Close</button>
                </div>
            </div>
        </div>
    `;
}

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// ─── Create Game Page ───────────────────────────────

function renderCreatePage() {
    const f = state.createForm;
    return `
        <div class="fade-in create-game-page">
            <div class="section-header">
                <h2>Create Game</h2>
            </div>

            <div style="background:#FFF3CD;border:1px solid #FFECB5;border-left:4px solid #FFC107;border-radius:8px;padding:12px 14px;margin-bottom:16px;font-size:0.82rem;color:#664D03;line-height:1.5">
                <strong>⚠️ Important:</strong> This is not a replacement for the court booking system and has no interaction with the West Hants court booking system. You <strong>MUST</strong> book the court first in Elite-Live before creating a game in this app.
            </div>

            <form id="create-game-form">
                <div class="form-group">
                    <label>Court</label>
                    <div class="court-selector">
                        ${COURTS.map((court, i) => `
                            <div class="court-option ${f.court === court ? 'selected' : ''}" data-court="${court}">
                                <div class="court-icon">🏟️</div>
                                <div class="court-name">${court}</div>
                            </div>
                        `).join('')}
                    </div>
                </div>

                <div class="form-group">
                    <label>Date</label>
                    <input type="date" class="form-input" name="game_date" 
                           value="${f.game_date}" min="${todayISO()}" required>
                </div>

                <div class="form-group">
                    <label>Time Slot</label>
                    <div class="time-grid" id="time-grid">
                        ${getTimeSlotsForDate(f.game_date).map(t => `
                            <div class="time-slot ${f.start_time === t ? 'selected' : ''}" data-time="${t}">
                                ${t}
                            </div>
                        `).join('')}
                    </div>
                </div>

                <div class="form-group">
                    <label>Allowed Skill Levels</label>
                    <p class="form-hint">Select the range of levels that can join this game</p>
                    <div class="level-range" id="level-range">
                        ${SKILL_LEVELS.map(l => {
                            const inRange = l.value >= f.min_level && l.value <= f.max_level;
                            return `
                                <div class="level-pill ${inRange ? 'in-range' : ''}" 
                                     data-level="${l.value}"
                                     style="${inRange ? `background:${l.color}; border-color:${l.color}` : ''}">
                                    <span class="pill-dot" style="background:${l.color}"></span>
                                    ${l.name}
                                </div>
                            `;
                        }).join('')}
                    </div>
                </div>

                <div class="form-group">
                    <label>Looking For Players</label>
                    <p class="form-hint">How many players do you need from the app? You + reserved guests fill the rest.</p>
                    <select class="form-input" name="reserved_slots">
                        <option value="0" ${f.reserved_slots===0?'selected':''}>Need 3 players (just me so far)</option>
                        <option value="1" ${f.reserved_slots===1?'selected':''}>Need 2 players (I have 1 guest)</option>
                        <option value="2" ${f.reserved_slots===2?'selected':''}>Need 1 player (I have 2 guests)</option>
                    </select>
                </div>

                <div class="form-group">
                    <label>Notes (optional)</label>
                    <input type="text" class="form-input" name="notes" placeholder="e.g. Friendly match, all welcome!" maxlength="200">
                </div>

                <div id="create-error" class="form-error mb-8" style="display:none"></div>

                <button type="submit" class="btn btn-primary btn-block mt-16">Create Game</button>
                <button type="button" class="btn btn-secondary btn-block mt-8" onclick="navigateTo('games')">Cancel</button>
            </form>
        </div>
    `;
}

// ─── Courts Page ────────────────────────────────────

function renderCourtsPage() {
    return `
        <div class="fade-in">
            <div class="section-header">
                <h2>Court Availability</h2>
            </div>

            <div class="date-selector">
                <input type="date" class="form-input" id="court-date" 
                       value="${state.courtDate}" min="${todayISO()}">
            </div>

            <div id="court-grid-container">
                ${state.courtAvailability ? renderCourtGrid() : '<div class="text-center" style="padding:20px"><div class="loader" style="margin:0 auto"></div></div>'}
            </div>
        </div>
    `;
}

function renderCourtGrid() {
    if (!state.courtAvailability) return '';
    const avail = state.courtAvailability.availability;
    const slots = getTimeSlotsForDate(state.courtDate);

    let html = `<div class="court-grid">`;
    // Header row
    html += `<div class="court-grid-header" style="background:transparent"></div>`;
    COURTS.forEach(c => {
        html += `<div class="court-grid-header">${c}</div>`;
    });

    slots.forEach(slot => {
        html += `<div class="court-grid-time">${slot}</div>`;
        COURTS.forEach(court => {
            const slotData = avail[court] && avail[court][slot];
            if (slotData && slotData.past) {
                html += `<div class="court-slot past" title="Past">—</div>`;
            } else if (slotData && !slotData.available && slotData.game) {
                const game = slotData.game;
                const level = getSkillLevel(game.min_level);
                html += `<div class="court-slot booked" data-game-id="${game.id}" style="border-left:3px solid ${level.color}" title="${escapeHtml(game.creator_name)}'s game">
                    <span class="slot-level" style="color:${level.color}">${level.name}</span>
                    <span class="slot-players">${game.player_count + (game.reserved_slots || 0)}/${game.max_players}</span>
                </div>`;
            } else if (slotData && !slotData.available) {
                html += `<div class="court-slot booked" title="Booked">●</div>`;
            } else {
                html += `<div class="court-slot available" data-court="${court}" data-time="${slot}" title="Available">✓</div>`;
            }
        });
    });

    html += `</div>`;
    return html;
}

// ─── Profile Page ───────────────────────────────────

function renderProfilePage() {
    const level = getSkillLevel(state.user.skill_level);
    return `
        <div class="fade-in">
            <div class="card">
                <div class="profile-header">
                    <div class="profile-avatar" style="background:${level.color}">${getInitials(state.user)}</div>
                    <h2>${escapeHtml(state.user.first_name || '')} ${escapeHtml(state.user.last_name || '')}</h2>
                    <div class="profile-email">@${escapeHtml(state.user.username)} · ${escapeHtml(state.user.email)}</div>
                    <div class="profile-level" style="background:${level.color}">
                        ${level.name} – ${level.label}
                    </div>
                </div>
            </div>

            <div class="card mt-16">
                <h3 style="font-size:1rem;font-weight:700;margin-bottom:12px;">Edit Name</h3>
                <div class="form-row">
                    <div class="form-group">
                        <label>First Name</label>
                        <input type="text" class="form-input" id="edit-first-name" value="${escapeHtml(state.user.first_name || '')}" required>
                    </div>
                    <div class="form-group">
                        <label>Last Name</label>
                        <input type="text" class="form-input" id="edit-last-name" value="${escapeHtml(state.user.last_name || '')}" required>
                    </div>
                </div>
                <button class="btn btn-primary btn-block mt-8" id="btn-save-name" disabled>Save Name</button>
                <div id="name-save-status" style="text-align:center;margin-top:8px;font-size:0.8rem;display:none"></div>
            </div>

            <div class="card mt-16">
                <h3 style="font-size:1rem;font-weight:700;margin-bottom:12px;">Change Password</h3>
                <div class="form-group">
                    <label>Current Password</label>
                    <input type="password" class="form-input" id="current-password" autocomplete="current-password">
                </div>
                <div class="form-group">
                    <label>New Password</label>
                    <input type="password" class="form-input" id="new-password" autocomplete="new-password">
                </div>
                <div class="form-group">
                    <label>Confirm New Password</label>
                    <input type="password" class="form-input" id="confirm-password" autocomplete="new-password">
                </div>
                <div class="password-requirements" style="font-size:0.75rem;color:var(--text-secondary);margin-bottom:8px">
                    Must be 8+ characters with letters, numbers and special characters
                </div>
                <button class="btn btn-primary btn-block" id="btn-change-password" disabled>Change Password</button>
                <div id="password-save-status" style="text-align:center;margin-top:8px;font-size:0.8rem;display:none"></div>
            </div>

            <div class="card mt-16">
                <h3 style="font-size:1rem;font-weight:700;margin-bottom:12px;">Change Colour Grading</h3>
                <p style="font-size:0.8rem;color:var(--text-secondary);margin-bottom:12px;">
                    Select your current West Hants colour grading:
                </p>
                <div class="skill-selector" id="profile-skill-selector">
                    ${SKILL_LEVELS.map(l => `
                        <div class="skill-option ${l.value === state.user.skill_level ? 'selected' : ''}" data-value="${l.value}">
                            <div class="color-swatch" style="background:${l.color}"></div>
                            <div>
                                <div class="skill-name">${l.name}</div>
                                <div class="skill-desc">${l.label}</div>
                            </div>
                        </div>
                    `).join('')}
                </div>
                <button class="btn btn-primary btn-block mt-16" id="btn-save-level" disabled>Save Colour Grading</button>
                <div id="level-save-status" style="text-align:center;margin-top:8px;font-size:0.8rem;display:none"></div>
            </div>

            <div class="card mt-16">
                <h3 style="font-size:1rem;font-weight:700;margin-bottom:12px;">Colour Grading Guide</h3>
                <p style="font-size:0.8rem;color:var(--text-secondary);margin-bottom:12px;">
                    The West Hants Colour Grading System follows snooker ball colours from lowest to highest:
                </p>
                ${SKILL_LEVELS.map(l => `
                    <div class="grading-card" style="padding:12px;margin-bottom:8px;border-radius:8px;border-left:4px solid ${l.color};background:var(--bg-secondary)">
                        <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
                            <div style="width:20px;height:20px;border-radius:50%;background:${l.color};flex-shrink:0;border:2px solid rgba(0,0,0,0.1)"></div>
                            <span style="font-weight:700;font-size:0.95rem">${l.name}</span>
                            <span style="color:var(--text-secondary);font-size:0.8rem">${l.label}</span>
                        </div>
                        <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px 12px;font-size:0.78rem">
                            <div><span style="color:var(--text-secondary)">Technique:</span> ${l.technique}</div>
                            <div><span style="color:var(--text-secondary)">Tactical:</span> ${l.tactical}</div>
                            <div><span style="color:var(--text-secondary)">Movement:</span> ${l.movement}</div>
                            <div><span style="color:var(--text-secondary)">Pace:</span> ${l.pace}</div>
                        </div>
                    </div>
                `).join('')}
            </div>

            <button class="btn btn-danger btn-block mt-24" id="btn-logout">Sign Out</button>

            <div class="text-center mt-16" style="font-size:0.75rem;color:var(--text-light)">
                West Hants Padel Matchmaker v1.0
            </div>
        </div>
    `;
}

// ═══════════════════════════════════════════════════
// Navigation
// ═══════════════════════════════════════════════════

async function navigateTo(page, options = {}) {
    state.currentPage = page;
    const content = $('#page-content');
    const fab = $('#fab-create');

    // Update nav active state
    $$('.nav-item').forEach(item => {
        item.classList.toggle('active', item.dataset.page === page);
    });

    // Show/hide FAB
    if (fab) {
        fab.style.display = (page === 'games' || page === 'my-games' || page === 'courts') ? 'flex' : 'none';
    }

    switch (page) {
        case 'games':
            content.innerHTML = '<div class="text-center" style="padding:40px"><div class="loader" style="margin:0 auto"></div></div>';
            try {
                await fetchGames();
                content.innerHTML = renderGamesPage();
                bindGamesEvents();
            } catch (err) {
                content.innerHTML = `<div class="empty-state"><div class="icon">⚠️</div><h3>Error loading games</h3><p>${escapeHtml(err.message)}</p></div>`;
            }
            break;

        case 'my-games':
            content.innerHTML = '<div class="text-center" style="padding:40px"><div class="loader" style="margin:0 auto"></div></div>';
            try {
                await fetchMyGames();
                content.innerHTML = renderMyGamesPage();
                bindMyGamesEvents();
            } catch (err) {
                content.innerHTML = `<div class="empty-state"><div class="icon">⚠️</div><h3>Error loading your games</h3><p>${escapeHtml(err.message)}</p></div>`;
            }
            break;

        case 'create':
            // Reset form defaults
            state.createForm.court = null;
            state.createForm.start_time = null;
            state.createForm.game_date = todayISO();
            state.createForm.min_level = 1;
            state.createForm.max_level = 7;
            state.createForm.reserved_slots = 0;
            state.createForm.notes = '';
            // Apply any pre-filled values (e.g. from courts page)
            if (options.prefill) {
                Object.assign(state.createForm, options.prefill);
            }
            content.innerHTML = renderCreatePage();
            bindCreateEvents();
            updateTimeSlotAvailability();
            break;

        case 'courts':
            content.innerHTML = renderCourtsPage();
            bindCourtsEvents();
            loadCourtAvailability();
            break;

        case 'profile':
            content.innerHTML = renderProfilePage();
            bindProfileEvents();
            break;
    }
}

// ═══════════════════════════════════════════════════
// Event Binding
// ═══════════════════════════════════════════════════

function bindAuthEvents() {
    // Tab switching
    document.addEventListener('click', (e) => {
        const tab = e.target.closest('.auth-tab');
        if (tab) {
            $$('.auth-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            const content = $('#auth-content');
            if (tab.dataset.tab === 'login') {
                content.innerHTML = renderLoginForm();
                bindForgotPasswordLink();
            } else {
                content.innerHTML = renderRegisterForm();
            }
        }
    });

    // Forgot password link on initial render
    bindForgotPasswordLink();

    // Login form
    document.addEventListener('submit', async (e) => {
        if (e.target.id === 'login-form') {
            e.preventDefault();
            const form = new FormData(e.target);
            const errorEl = $('#login-error');
            const submitBtn = e.target.querySelector('button[type="submit"]');
            submitBtn.disabled = true;
            submitBtn.textContent = 'Signing in...';
            try {
                await login(form.get('username'), form.get('password'));
                render();
            } catch (err) {
                errorEl.textContent = err.message;
                errorEl.style.display = 'block';
                submitBtn.disabled = false;
                submitBtn.textContent = 'Sign In';
            }
        }

        if (e.target.id === 'register-form') {
            e.preventDefault();
            const form = new FormData(e.target);
            const errorEl = $('#register-error');
            const skillLevel = parseInt(form.get('skill_level'));

            if (!skillLevel) {
                errorEl.textContent = 'Please select your skill level';
                errorEl.style.display = 'block';
                return;
            }

            const pwError = validatePassword(form.get('password'));
            if (pwError) {
                errorEl.textContent = pwError;
                errorEl.style.display = 'block';
                return;
            }

            const submitBtn = e.target.querySelector('button[type="submit"]');
            submitBtn.disabled = true;
            submitBtn.textContent = 'Creating account...';

            try {
                await register({
                    username: form.get('username'),
                    email: form.get('email'),
                    password: form.get('password'),
                    skill_level: skillLevel,
                    first_name: form.get('first_name'),
                    last_name: form.get('last_name'),
                });
                showToast('Check your email for a verification code! 📧', 'success');
                render();
            } catch (err) {
                errorEl.textContent = err.message;
                errorEl.style.display = 'block';
                submitBtn.disabled = false;
                submitBtn.textContent = 'Create Account';
            }
        }
    });

    // Skill level selector
    document.addEventListener('click', (e) => {
        const option = e.target.closest('.skill-option');
        if (option) {
            $$('.skill-option').forEach(o => o.classList.remove('selected'));
            option.classList.add('selected');
            const input = $('#skill-level-input');
            if (input) input.value = option.dataset.value;
        }
    });
}

function bindForgotPasswordLink() {
    const btn = $('#forgot-password-btn');
    if (btn) {
        btn.addEventListener('click', () => {
            const content = $('#auth-content');
            content.innerHTML = renderForgotPasswordForm();
            bindForgotPasswordEvents();
        });
    }
}

function renderForgotPasswordForm() {
    return `
        <div class="forgot-password-form">
            <p style="color:#666; font-size:14px; margin-bottom:16px; text-align:center;">
                Enter your username or email address and we'll send you a code to reset your password.
            </p>
            <form id="forgot-form">
                <div class="form-group">
                    <label>Username or Email</label>
                    <input type="text" class="form-input" name="identifier" placeholder="Enter your username or email" required autocomplete="username">
                </div>
                <div id="forgot-error" class="form-error mb-8" style="display:none"></div>
                <button type="submit" class="btn btn-primary btn-block mt-8">Send Reset Code</button>
            </form>
            <div style="text-align:center; margin-top:12px;">
                <button id="back-to-login-btn" class="btn btn-text" style="font-size:13px;">Back to Sign In</button>
            </div>
        </div>
    `;
}

function renderResetPasswordForm(identifier) {
    return `
        <div class="reset-password-form">
            <p style="color:#666; font-size:14px; margin-bottom:16px; text-align:center;">
                Enter the 6-digit code we sent to your email, along with your new password.
            </p>
            <form id="reset-form">
                <input type="hidden" name="identifier" value="${identifier}">
                <div class="form-group">
                    <label>Reset Code</label>
                    <input type="text" class="form-input" name="code"
                           placeholder="000000" required maxlength="6" pattern="[0-9]{6}"
                           inputmode="numeric" autocomplete="one-time-code"
                           style="text-align:center; font-size:24px; letter-spacing:8px; font-weight:700">
                </div>
                <div class="form-group">
                    <label>New Password</label>
                    <input type="password" class="form-input" name="new_password" placeholder="Min 8 characters, letters + numbers + special" required minlength="8" autocomplete="new-password">
                </div>
                <div id="reset-error" class="form-error mb-8" style="display:none"></div>
                <button type="submit" class="btn btn-primary btn-block mt-8">Reset Password</button>
            </form>
            <div style="text-align:center; margin-top:12px;">
                <button id="back-to-login-btn" class="btn btn-text" style="font-size:13px;">Back to Sign In</button>
            </div>
        </div>
    `;
}

function bindForgotPasswordEvents() {
    const form = $('#forgot-form');
    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const identifier = new FormData(form).get('identifier').trim();
            const errorEl = $('#forgot-error');
            const submitBtn = form.querySelector('button[type="submit"]');
            submitBtn.disabled = true;
            submitBtn.textContent = 'Sending...';
            try {
                await forgotPassword(identifier);
                showToast('If an account exists, a reset code has been sent 📧', 'success');
                const content = $('#auth-content');
                content.innerHTML = renderResetPasswordForm(identifier);
                bindResetPasswordEvents();
            } catch (err) {
                errorEl.textContent = err.message;
                errorEl.style.display = 'block';
                submitBtn.disabled = false;
                submitBtn.textContent = 'Send Reset Code';
            }
        });
    }

    const backBtn = $('#back-to-login-btn');
    if (backBtn) {
        backBtn.addEventListener('click', () => {
            const content = $('#auth-content');
            content.innerHTML = renderLoginForm();
            bindForgotPasswordLink();
            $$('.auth-tab').forEach(t => t.classList.remove('active'));
            const loginTab = document.querySelector('.auth-tab[data-tab=\"login\"]');
            if (loginTab) loginTab.classList.add('active');
        });
    }
}

function bindResetPasswordEvents() {
    const form = $('#reset-form');
    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const fd = new FormData(form);
            const errorEl = $('#reset-error');
            const submitBtn = form.querySelector('button[type="submit"]');

            const pwError = validatePassword(fd.get('new_password'));
            if (pwError) {
                errorEl.textContent = pwError;
                errorEl.style.display = 'block';
                return;
            }

            submitBtn.disabled = true;
            submitBtn.textContent = 'Resetting...';
            try {
                await resetPassword(
                    fd.get('identifier'),
                    fd.get('code').trim(),
                    fd.get('new_password')
                );
                showToast('Password reset! You can now sign in. ✅', 'success');
                const content = $('#auth-content');
                content.innerHTML = renderLoginForm();
                bindForgotPasswordLink();
                $$('.auth-tab').forEach(t => t.classList.remove('active'));
                const loginTab = document.querySelector('.auth-tab[data-tab=\"login\"]');
                if (loginTab) loginTab.classList.add('active');
            } catch (err) {
                errorEl.textContent = err.message;
                errorEl.style.display = 'block';
                submitBtn.disabled = false;
                submitBtn.textContent = 'Reset Password';
            }
        });
    }

    const backBtn = $('#back-to-login-btn');
    if (backBtn) {
        backBtn.addEventListener('click', () => {
            const content = $('#auth-content');
            content.innerHTML = renderLoginForm();
            bindForgotPasswordLink();
            $$('.auth-tab').forEach(t => t.classList.remove('active'));
            const loginTab = document.querySelector('.auth-tab[data-tab=\"login\"]');
            if (loginTab) loginTab.classList.add('active');
        });
    }
}

function bindVerifyEvents() {
    const form = $('#verify-form');
    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const code = new FormData(form).get('code').trim();
            const errorEl = $('#verify-error');
            const submitBtn = form.querySelector('button[type="submit"]');
            submitBtn.disabled = true;
            submitBtn.textContent = 'Verifying...';
            try {
                await verifyEmail(code);
                showToast('Email verified! Welcome to West Hants Padel! 🏸', 'success');
                render();
            } catch (err) {
                errorEl.textContent = err.message;
                errorEl.style.display = 'block';
                submitBtn.disabled = false;
                submitBtn.textContent = 'Verify Email';
            }
        });
    }

    const resendBtn = $('#resend-btn');
    if (resendBtn) {
        resendBtn.addEventListener('click', async () => {
            resendBtn.disabled = true;
            resendBtn.textContent = 'Sending...';
            try {
                await resendVerification();
                showToast('New verification code sent! 📧', 'success');
                resendBtn.textContent = 'Code Sent!';
                setTimeout(() => {
                    resendBtn.disabled = false;
                    resendBtn.textContent = 'Resend Code';
                }, 30000);
            } catch (err) {
                showToast(err.message, 'error');
                resendBtn.disabled = false;
                resendBtn.textContent = 'Resend Code';
            }
        });
    }

    const logoutBtn = $('#verify-logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', async () => {
            await logout();
            render();
        });
    }
}

function bindMainEvents() {
    // Bottom nav
    $$('.nav-item').forEach(item => {
        item.addEventListener('click', () => navigateTo(item.dataset.page));
    });

    // FAB
    const fab = $('#fab-create');
    if (fab) {
        fab.addEventListener('click', () => navigateTo('create'));
    }
}

function bindGamesEvents() {
    // Skill level filters
    $$('#skill-filters .filter-chip').forEach(chip => {
        chip.addEventListener('click', async () => {
            const val = chip.dataset.filter;
            state.skillFilter = val ? parseInt(val) : null;
            await fetchGames();
            const content = $('#page-content');
            content.innerHTML = renderGamesPage();
            bindGamesEvents();
        });
    });

    // Game card click → open modal
    $$('.game-card').forEach(card => {
        card.addEventListener('click', async (e) => {
            // Don't open modal if clicking join button
            if (e.target.closest('.btn-quick-join')) return;
            const gameId = parseInt(card.dataset.gameId);
            await openGameModal(gameId);
        });
    });

    // Quick join
    $$('.btn-quick-join').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.stopPropagation();
            const gameId = parseInt(btn.dataset.gameId);
            btn.disabled = true;
            btn.textContent = 'Joining...';
            try {
                await joinGame(gameId);
                showToast('You joined the game! 🎉', 'success');
                await fetchGames();
                const content = $('#page-content');
                content.innerHTML = renderGamesPage();
                bindGamesEvents();
            } catch (err) {
                showToast(err.message, 'error');
                btn.disabled = false;
                btn.textContent = 'Join';
            }
        });
    });
}

function bindMyGamesEvents() {
    // Game card click → open modal
    $$('#my-games-list .game-card').forEach(card => {
        card.addEventListener('click', async () => {
            const gameId = parseInt(card.dataset.gameId);
            await openGameModal(gameId);
        });
    });
}

async function openGameModal(gameId) {
    try {
        const game = await fetchGame(gameId);
        document.body.insertAdjacentHTML('beforeend', renderGameModal(game));
        bindModalEvents(game);
    } catch (err) {
        showToast(err.message, 'error');
    }
}

function closeModal() {
    const modal = $('#game-modal');
    if (modal) modal.remove();
    const warning = $('#level-change-modal');
    if (warning) warning.remove();
}

function showLevelChangeWarning(newLevel, affectedGames) {
    const newLevelInfo = getSkillLevel(newLevel);
    const gameList = affectedGames.map(g =>
        `<li><strong>${g.court}</strong> — ${formatDate(g.game_date)} at ${g.start_time} (${g.min_level_name} – ${g.max_level_name})</li>`
    ).join('');

    const html = `
        <div class="modal-overlay" id="level-change-modal">
            <div class="modal-content">
                <div class="modal-handle"></div>
                <div class="modal-header">
                    <h2>⚠️ Level Change Warning</h2>
                </div>
                <div class="modal-body">
                    <p>Changing your colour grading to <strong style="color:${newLevelInfo.color}">${newLevelInfo.label}</strong> will remove you from the following game${affectedGames.length > 1 ? 's' : ''} because your new level is outside their required range:</p>
                    <ul class="affected-games-list">${gameList}</ul>
                    <p style="margin-top:12px"><strong>Do you want to continue?</strong></p>
                </div>
                <div class="modal-actions" style="display:flex;gap:8px;padding:16px">
                    <button class="btn btn-secondary" id="level-change-cancel" style="flex:1">Cancel</button>
                    <button class="btn btn-danger" id="level-change-confirm" style="flex:1">Change & Leave Games</button>
                </div>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', html);

    $('#level-change-cancel').addEventListener('click', closeModal);
    $('#level-change-modal').addEventListener('click', (e) => {
        if (e.target.id === 'level-change-modal') closeModal();
    });

    $('#level-change-confirm').addEventListener('click', async () => {
        const btn = $('#level-change-confirm');
        btn.disabled = true;
        btn.textContent = 'Updating...';
        try {
            const result = await updateSkillLevel(newLevel, true);
            closeModal();
            const removedMsg = result.removed_from > 0
                ? ` You were removed from ${result.removed_from} game${result.removed_from > 1 ? 's' : ''}.`
                : '';
            showToast(`Colour grading updated! 🎨${removedMsg}`, 'success');
            const content = $('#page-content');
            content.innerHTML = renderProfilePage();
            bindProfileEvents();
            const level = getSkillLevel(state.user.skill_level);
            const badge = $('.user-badge');
            if (badge) {
                badge.innerHTML = `<span class="level-dot" style="background:${level.color}"></span>${state.user.first_name || state.user.username}`;
            }
        } catch (err) {
            showToast(err.message, 'error');
            closeModal();
        }
    });
}

function bindModalEvents(game) {
    const modal = $('#game-modal');
    if (!modal) return;

    // Close on overlay click
    modal.addEventListener('click', (e) => {
        if (e.target === modal) closeModal();
    });

    // Close button
    const closeBtn = $('#modal-close-btn');
    if (closeBtn) closeBtn.addEventListener('click', closeModal);

    // Join
    const joinBtn = $('#modal-join-game');
    if (joinBtn) {
        joinBtn.addEventListener('click', async () => {
            joinBtn.disabled = true;
            joinBtn.textContent = 'Joining...';
            try {
                await joinGame(game.id);
                closeModal();
                showToast('You joined the game! 🎉', 'success');
                if (state.currentPage === 'games') {
                    await fetchGames();
                    const content = $('#page-content');
                    content.innerHTML = renderGamesPage();
                    bindGamesEvents();
                }
            } catch (err) {
                showToast(err.message, 'error');
                joinBtn.disabled = false;
                joinBtn.textContent = 'Join Game';
            }
        });
    }

    // Leave
    const leaveBtn = $('#modal-leave-game');
    if (leaveBtn) {
        leaveBtn.addEventListener('click', async () => {
            leaveBtn.disabled = true;
            leaveBtn.textContent = 'Leaving...';
            try {
                await leaveGame(game.id);
                closeModal();
                showToast('You left the game', 'success');
                if (state.currentPage === 'games') {
                    await fetchGames();
                    const content = $('#page-content');
                    content.innerHTML = renderGamesPage();
                    bindGamesEvents();
                }
            } catch (err) {
                showToast(err.message, 'error');
                leaveBtn.disabled = false;
                leaveBtn.textContent = 'Leave Game';
            }
        });
    }

    // Cancel game (creator)
    const cancelBtn = $('#modal-cancel-game');
    if (cancelBtn) {
        cancelBtn.addEventListener('click', async () => {
            if (!confirm('Are you sure you want to cancel this game? All players will be removed.')) return;
            cancelBtn.disabled = true;
            cancelBtn.textContent = 'Cancelling...';
            try {
                await leaveGame(game.id);
                closeModal();
                showToast('Game cancelled', 'success');
                if (state.currentPage === 'games') {
                    await fetchGames();
                    const content = $('#page-content');
                    content.innerHTML = renderGamesPage();
                    bindGamesEvents();
                }
            } catch (err) {
                showToast(err.message, 'error');
                cancelBtn.disabled = false;
                cancelBtn.textContent = 'Cancel Game';
            }
        });
    }
}

function bindCreateEvents() {
    // Court selection
    $$('.court-option').forEach(opt => {
        opt.addEventListener('click', () => {
            $$('.court-option').forEach(o => o.classList.remove('selected'));
            opt.classList.add('selected');
            state.createForm.court = opt.dataset.court;
            updateTimeSlotAvailability();
        });
    });

    // Date change
    const dateInput = $('input[name="game_date"]');
    if (dateInput) {
        dateInput.addEventListener('change', () => {
            state.createForm.game_date = dateInput.value;
            updateTimeSlotAvailability();
        });
    }

    // Time slot selection
    $$('.time-slot').forEach(slot => {
        slot.addEventListener('click', () => {
            if (slot.classList.contains('disabled')) return;
            $$('.time-slot').forEach(s => s.classList.remove('selected'));
            slot.classList.add('selected');
            state.createForm.start_time = slot.dataset.time;
        });
    });

    // Level range selection
    let rangeStart = null;
    $$('#level-range .level-pill').forEach(pill => {
        pill.addEventListener('click', () => {
            const val = parseInt(pill.dataset.level);
            if (rangeStart === null) {
                rangeStart = val;
                state.createForm.min_level = val;
                state.createForm.max_level = val;
            } else {
                const min = Math.min(rangeStart, val);
                const max = Math.max(rangeStart, val);
                state.createForm.min_level = min;
                state.createForm.max_level = max;
                rangeStart = null;
            }
            updateLevelRange();
        });
    });

    // Form submit
    const form = $('#create-game-form');
    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const errorEl = $('#create-error');
            const formData = new FormData(form);

            if (!state.createForm.court) {
                errorEl.textContent = 'Please select a court';
                errorEl.style.display = 'block';
                return;
            }
            if (!state.createForm.start_time) {
                errorEl.textContent = 'Please select a time slot';
                errorEl.style.display = 'block';
                return;
            }

            const submitBtn = form.querySelector('button[type="submit"]');
            submitBtn.disabled = true;
            submitBtn.textContent = 'Creating...';

            try {
                await createGame({
                    court: state.createForm.court,
                    game_date: state.createForm.game_date,
                    start_time: state.createForm.start_time,
                    min_level: state.createForm.min_level,
                    max_level: state.createForm.max_level,
                    reserved_slots: parseInt(formData.get('reserved_slots')),
                    notes: formData.get('notes') || '',
                });
                showToast('Game created! 🎉', 'success');
                navigateTo('games');
            } catch (err) {
                errorEl.textContent = err.message;
                errorEl.style.display = 'block';
                submitBtn.disabled = false;
                submitBtn.textContent = 'Create Game';
            }
        });
    }
}

function updateLevelRange() {
    $$('#level-range .level-pill').forEach(pill => {
        const val = parseInt(pill.dataset.level);
        const inRange = val >= state.createForm.min_level && val <= state.createForm.max_level;
        const level = getSkillLevel(val);
        pill.classList.toggle('in-range', inRange);
        if (inRange) {
            pill.style.background = level.color;
            pill.style.borderColor = level.color;
            pill.style.color = 'white';
        } else {
            pill.style.background = '';
            pill.style.borderColor = '';
            pill.style.color = '';
        }
    });
}

async function updateTimeSlotAvailability() {
    const f = state.createForm;
    const slots = getTimeSlotsForDate(f.game_date);

    // Rebuild time grid for the selected date's valid slots
    const grid = $('#time-grid');
    if (grid) {
        // Clear selection if it's no longer valid for this day
        if (f.start_time && !slots.includes(f.start_time)) {
            f.start_time = null;
        }
        grid.innerHTML = slots.map(t => `
            <div class="time-slot ${f.start_time === t ? 'selected' : ''}" data-time="${t}">
                ${t}
            </div>
        `).join('');
        // Rebind click events
        grid.querySelectorAll('.time-slot').forEach(slot => {
            slot.addEventListener('click', () => {
                if (slot.classList.contains('disabled')) return;
                grid.querySelectorAll('.time-slot').forEach(s => s.classList.remove('selected'));
                slot.classList.add('selected');
                state.createForm.start_time = slot.dataset.time;
            });
        });
    }

    // Disable past time slots when date is today
    const isToday = f.game_date === todayISO();
    const now = new Date();
    const currentHour = now.getHours();

    $$('.time-slot').forEach(slot => {
        const time = slot.dataset.time;
        const slotHour = parseInt(time.split(':')[0]);
        if (isToday && slotHour <= currentHour) {
            slot.classList.add('disabled');
            slot.classList.remove('selected');
            if (f.start_time === time) {
                f.start_time = null;
            }
        }
    });

    if (!f.court || !f.game_date) return;

    try {
        const data = await fetchCourtAvailability(f.game_date);
        const courtAvail = data.availability[f.court];

        $$('.time-slot').forEach(slot => {
            const time = slot.dataset.time;
            if (courtAvail && courtAvail[time] && !courtAvail[time].available) {
                slot.classList.add('disabled');
                slot.classList.remove('selected');
                if (f.start_time === time) {
                    f.start_time = null;
                }
            }
        });
    } catch (err) {
        // Silently fail - availability check is optional
    }
}

function bindCourtsEvents() {
    const dateInput = $('#court-date');
    if (dateInput) {
        dateInput.addEventListener('change', () => {
            state.courtDate = dateInput.value;
            loadCourtAvailability();
        });
    }
}

async function loadCourtAvailability() {
    try {
        const data = await fetchCourtAvailability(state.courtDate);
        state.courtAvailability = data;
        const container = $('#court-grid-container');
        if (container) {
            container.innerHTML = renderCourtGrid();
            // Bind court grid clicks
            container.querySelectorAll('.court-slot.available').forEach(slot => {
                slot.addEventListener('click', () => {
                    navigateTo('create', {
                        prefill: {
                            court: slot.dataset.court,
                            game_date: state.courtDate,
                            start_time: slot.dataset.time,
                        }
                    });
                });
            });
            container.querySelectorAll('.court-slot.booked').forEach(slot => {
                slot.addEventListener('click', async () => {
                    const gameId = parseInt(slot.dataset.gameId);
                    if (gameId) await openGameModal(gameId);
                });
            });
        }
    } catch (err) {
        const container = $('#court-grid-container');
        if (container) {
            container.innerHTML = `<div class="empty-state"><p>Error loading availability</p></div>`;
        }
    }
}

function bindProfileEvents() {
    let selectedLevel = state.user.skill_level;

    // ── Edit Name ──
    const firstNameInput = $('#edit-first-name');
    const lastNameInput = $('#edit-last-name');
    const saveNameBtn = $('#btn-save-name');
    function checkNameChanged() {
        if (!saveNameBtn) return;
        const changed = firstNameInput.value.trim() !== (state.user.first_name || '') ||
                        lastNameInput.value.trim() !== (state.user.last_name || '');
        saveNameBtn.disabled = !changed || !firstNameInput.value.trim() || !lastNameInput.value.trim();
    }
    if (firstNameInput) firstNameInput.addEventListener('input', checkNameChanged);
    if (lastNameInput) lastNameInput.addEventListener('input', checkNameChanged);
    if (saveNameBtn) {
        saveNameBtn.addEventListener('click', async () => {
            saveNameBtn.disabled = true;
            saveNameBtn.textContent = 'Saving...';
            try {
                await updateName(firstNameInput.value.trim(), lastNameInput.value.trim());
                showToast('Name updated! ✅', 'success');
                const content = $('#page-content');
                content.innerHTML = renderProfilePage();
                bindProfileEvents();
                const level = getSkillLevel(state.user.skill_level);
                const badge = $('.user-badge');
                if (badge) {
                    badge.innerHTML = `<span class="level-dot" style="background:${level.color}"></span>${state.user.first_name || state.user.username}`;
                }
            } catch (err) {
                showToast(err.message, 'error');
                saveNameBtn.disabled = false;
                saveNameBtn.textContent = 'Save Name';
            }
        });
    }

    // ── Change Password ──
    const currentPw = $('#current-password');
    const newPw = $('#new-password');
    const confirmPw = $('#confirm-password');
    const changePwBtn = $('#btn-change-password');
    const pwStatus = $('#password-save-status');
    function checkPasswordReady() {
        if (!changePwBtn) return;
        changePwBtn.disabled = !currentPw.value || !newPw.value || !confirmPw.value;
    }
    if (currentPw) currentPw.addEventListener('input', checkPasswordReady);
    if (newPw) newPw.addEventListener('input', checkPasswordReady);
    if (confirmPw) confirmPw.addEventListener('input', checkPasswordReady);
    if (changePwBtn) {
        changePwBtn.addEventListener('click', async () => {
            if (pwStatus) { pwStatus.style.display = 'none'; }
            if (newPw.value !== confirmPw.value) {
                if (pwStatus) {
                    pwStatus.textContent = 'New passwords do not match';
                    pwStatus.style.display = 'block';
                    pwStatus.style.color = 'var(--danger)';
                }
                return;
            }
            const pwError = validatePassword(newPw.value);
            if (pwError) {
                if (pwStatus) {
                    pwStatus.textContent = pwError;
                    pwStatus.style.display = 'block';
                    pwStatus.style.color = 'var(--danger)';
                }
                return;
            }
            changePwBtn.disabled = true;
            changePwBtn.textContent = 'Changing...';
            try {
                await changePassword(currentPw.value, newPw.value);
                showToast('Password changed! 🔒', 'success');
                currentPw.value = '';
                newPw.value = '';
                confirmPw.value = '';
                changePwBtn.disabled = true;
                changePwBtn.textContent = 'Change Password';
                if (pwStatus) {
                    pwStatus.textContent = 'Password changed successfully';
                    pwStatus.style.display = 'block';
                    pwStatus.style.color = 'var(--success)';
                }
            } catch (err) {
                if (pwStatus) {
                    pwStatus.textContent = err.message;
                    pwStatus.style.display = 'block';
                    pwStatus.style.color = 'var(--danger)';
                }
                showToast(err.message, 'error');
                changePwBtn.disabled = false;
                changePwBtn.textContent = 'Change Password';
            }
        });
    }

    // ── Skill level selector ──
    $$('#profile-skill-selector .skill-option').forEach(option => {
        option.addEventListener('click', () => {
            $$('#profile-skill-selector .skill-option').forEach(o => o.classList.remove('selected'));
            option.classList.add('selected');
            selectedLevel = parseInt(option.dataset.value);
            const saveBtn = $('#btn-save-level');
            if (saveBtn) {
                saveBtn.disabled = (selectedLevel === state.user.skill_level);
            }
        });
    });

    // Save button
    const saveBtn = $('#btn-save-level');
    if (saveBtn) {
        saveBtn.addEventListener('click', async () => {
            saveBtn.disabled = true;
            saveBtn.textContent = 'Saving...';
            const statusEl = $('#level-save-status');
            try {
                const result = await updateSkillLevel(selectedLevel);
                if (result.affected_games) {
                    showLevelChangeWarning(selectedLevel, result.affected_games);
                    saveBtn.disabled = false;
                    saveBtn.textContent = 'Save Colour Grading';
                    return;
                }
                const removedMsg = result.removed_from > 0
                    ? ` You were removed from ${result.removed_from} incompatible game${result.removed_from > 1 ? 's' : ''}.`
                    : '';
                showToast(`Colour grading updated! 🎨${removedMsg}`, 'success');
                const content = $('#page-content');
                content.innerHTML = renderProfilePage();
                bindProfileEvents();
                const level = getSkillLevel(state.user.skill_level);
                const badge = $('.user-badge');
                if (badge) {
                    badge.innerHTML = `<span class="level-dot" style="background:${level.color}"></span>${state.user.first_name || state.user.username}`;
                }
            } catch (err) {
                if (statusEl) {
                    statusEl.textContent = err.message;
                    statusEl.style.display = 'block';
                    statusEl.style.color = 'var(--danger)';
                }
                showToast(err.message, 'error');
                saveBtn.disabled = false;
                saveBtn.textContent = 'Save Colour Grading';
            }
        });
    }

    // Logout
    const logoutBtn = $('#btn-logout');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', async () => {
            await logout();
            render();
            showToast('Signed out', 'success');
        });
    }
}

// ═══════════════════════════════════════════════════
// App Initialization
// ═══════════════════════════════════════════════════

async function init() {
    await checkAuth();
    render();
}

// Register service worker for PWA
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js').catch(() => {});
    });
}

// Start the app
init();
