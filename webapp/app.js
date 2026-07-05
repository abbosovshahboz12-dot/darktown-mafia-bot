// Initialize Telegram WebApp
const tg = window.Telegram.WebApp;
tg.expand();
tg.ready();

// Apply Telegram theme colors if desired
document.documentElement.style.setProperty('--bg-color', tg.backgroundColor || '#0d071b');

// Determine current user ID
// Try from Telegram initData first, then fallback to URL parameter (for browser testing)
let userId = 0;
let userFirstName = "Sh.Abbosov";
let userUsername = "";

if (tg.initDataUnsafe && tg.initDataUnsafe.user) {
    userId = tg.initDataUnsafe.user.id;
    userFirstName = tg.initDataUnsafe.user.first_name;
    userUsername = tg.initDataUnsafe.user.username || "";
} else {
    // Fallback to URL query parameter
    const urlParams = new URLSearchParams(window.location.search);
    userId = parseInt(urlParams.get('user_id')) || 7759713314; // Sh.Abbosov Telegram ID
    userUsername = "sh_abbosov";
}

// Global state
let userData = null;
let currentRoomId = null;
let currentPartyId = null;

// Auto-join party if start parameter contains party ID
if (tg.initDataUnsafe && tg.initDataUnsafe.start_param) {
    const param = tg.initDataUnsafe.start_param;
    if (param.startsWith('party_')) {
        autoJoinParty(param);
    }
}

async function autoJoinParty(partyId) {
    try {
        await fetch('/api/party/join', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, party_id: partyId })
        });
    } catch(e) {
        console.error("Auto join party error:", e);
    }
}

// Tab navigation
const navItems = document.querySelectorAll('.nav-item');
const tabContents = document.querySelectorAll('.tab-content');

navItems.forEach(item => {
    item.addEventListener('click', () => {
        const tabName = item.getAttribute('data-tab');
        
        // Update nav items
        navItems.forEach(nav => nav.classList.remove('active'));
        item.classList.add('active');
        
        // Update tabs
        tabContents.forEach(content => content.classList.remove('active'));
        document.getElementById(`tab-${tabName}`).classList.add('active');
        
        // Actions on tab click
        if (tabName === 'leaderboard') {
            loadLeaderboard();
        } else if (tabName === 'shop' || tabName === 'profile') {
            loadProfile();
        } else if (tabName === 'match') {
            loadActiveGame();
        } else if (tabName === 'admin') {
            loadAdminStats();
        }
    });
});

// Load Profile and Stats
async function loadProfile() {
    try {
        const response = await fetch(`/api/profile?user_id=${userId}`);
        if (!response.ok) throw new Error("Profile fetch failed");
        
        const data = await response.json();
        userData = data;
        
        if (data.isAdmin) {
            document.getElementById('nav-admin').style.display = 'inline-block';
        }
        
        // Render profile details
        document.getElementById('user-name').innerText = data.user.first_name || userFirstName;
        document.getElementById('user-username').innerText = data.user.username ? `@${data.user.username}` : userUsername;
        document.getElementById('user-coins').innerText = data.user.coins;
        document.getElementById('user-level').innerText = `Lvl ${data.user.level}`;
        
        // Avatar letter
        const firstLetter = (data.user.first_name || "M").charAt(0).toUpperCase();
        document.getElementById('user-avatar').innerText = firstLetter;
        
        // XP progress
        const xp = data.user.xp;
        const xpNeeded = data.user.level * 500;
        const xpPercent = Math.min((xp / xpNeeded) * 100, 100);
        document.getElementById('xp-text').innerText = `${xp} / ${xpNeeded} XP`;
        document.getElementById('xp-fill').style.width = `${xpPercent}%`;
        
        // Stats
        let totalPlayed = 0;
        let totalWon = 0;
        
        // Render role wins list
        const rolesStatsContainer = document.getElementById('roles-stats');
        rolesStatsContainer.innerHTML = '';
        
        const roleEmojis = {
            "mafia": "🔴",
            "don": "🕶️",
            "civilian": "🟢",
            "detective": "🔵",
            "doctor": "🟡",
            "bodyguard": "🛡️",
            "courtesan": "🌸",
            "maniac": "🦹"
        };
        
        if (data.stats && data.stats.length > 0) {
            data.stats.forEach(stat => {
                totalPlayed += stat.games_played;
                totalWon += stat.games_won;
                
                const roleKey = stat.role.toLowerCase();
                const emoji = roleEmojis[roleKey] || "🎭";
                const roleTitle = stat.role.charAt(0).toUpperCase() + stat.role.slice(1);
                
                const item = document.createElement('div');
                item.className = 'role-stat-item';
                item.innerHTML = `
                    <div class="role-info">
                        <span class="role-emoji">${emoji}</span>
                        <div>
                            <div class="role-name">${roleTitle}</div>
                            <div class="role-played">${stat.games_played} o'yin</div>
                        </div>
                    </div>
                    <span class="role-win-badge">${stat.games_won} yutuq</span>
                `;
                rolesStatsContainer.appendChild(item);
            });
        } else {
            rolesStatsContainer.innerHTML = '<div class="no-data">Hozircha o\'yinlar o\'ynalmagan.</div>';
        }
        
        document.getElementById('stats-played').innerText = totalPlayed;
        document.getElementById('stats-won').innerText = totalWon;
        const winRate = totalPlayed > 0 ? ((totalWon / totalPlayed) * 100).toFixed(1) : 0;
        document.getElementById('stats-rate').innerText = `${winRate}%`;
        
        // Shield active check
        const shieldActive = data.user.shield_active === 1;
        document.getElementById('shield-status').innerText = shieldActive ? "Faol (Yutqazsangiz XP himoya qilinadi)" : "Faol emas";
        document.getElementById('shield-status').style.color = shieldActive ? "var(--success)" : "var(--text-muted)";
        
        // Render inventory
        renderInventory(data.inventory, shieldActive);
        
        // Update localization and fields
        updateLang(data.user.language || 'uz');
        updateDailyClaimTimer(data.user.last_daily_claim);
        renderAchievements(data.stats, data.user.level);
        
    } catch (e) {
        console.error(e);
    }
}

// Render inventory items list
function renderInventory(inventory, shieldActive) {
    const list = document.getElementById('inventory-list');
    list.innerHTML = '';
    
    const items = {
        "shield": { name: "XP Qalqoni", icon: "🛡️", type: "shield" },
        "booster_mafia": { name: "Mafiya Booster", icon: "🔴", type: "booster" },
        "booster_detective": { name: "Komissar Booster", icon: "🔵", type: "booster" },
        "booster_doctor": { name: "Shifokor Booster", icon: "🟡", type: "booster" },
        "booster_maniac": { name: "Telba Booster", icon: "🦹", type: "booster" }
    };
    
    let hasItems = false;
    
    for (let key in inventory) {
        const qty = inventory[key];
        if (qty > 0 && items[key]) {
            hasItems = true;
            const itemDef = items[key];
            const div = document.createElement('div');
            div.className = 'inventory-item';
            
            let actionBtnHtml = '';
            if (itemDef.type === 'shield' && !shieldActive) {
                actionBtnHtml = `<button class="btn btn-sm btn-secondary" onclick="activateShield()">Faollashtirish</button>`;
            } else if (itemDef.type === 'booster') {
                actionBtnHtml = `<span style="font-size:0.75rem; color:var(--text-muted);">Bot guruhida /boost yozib faollashtiring</span>`;
            }
            
            div.innerHTML = `
                <div style="display:flex; align-items:center; gap:10px;">
                    <span style="font-size:1.4rem;">${itemDef.icon}</span>
                    <div>
                        <div style="font-weight:600; font-size:0.9rem;">${itemDef.name}</div>
                        <div style="font-size:0.75rem; color:var(--text-muted);">Soni: ${qty} dona</div>
                    </div>
                </div>
                ${actionBtnHtml}
            `;
            list.appendChild(div);
        }
    }
    
    if (!hasItems) {
        list.innerHTML = '<div class="no-data">Sizda sotib olingan narsalar yo\'q.</div>';
    }
}

// Load Global Leaderboard
async function loadLeaderboard() {
    try {
        const response = await fetch('/api/leaderboard');
        if (!response.ok) throw new Error("Leaderboard fetch failed");
        
        const data = await response.json();
        const list = document.getElementById('leaderboard-list');
        list.innerHTML = '';
        
        data.leaderboard.forEach((leader, idx) => {
            const row = document.createElement('div');
            row.className = 'leader-item';
            
            const firstLetter = (leader.first_name || "M").charAt(0).toUpperCase();
            const usernameHtml = leader.username ? `<span class="leader-username">@${leader.username}</span>` : '';
            
            row.innerHTML = `
                <div class="leader-rank">${idx + 1}</div>
                <div class="leader-avatar">${firstLetter}</div>
                <div class="leader-name">
                    ${leader.first_name}
                    ${usernameHtml}
                </div>
                <div class="leader-score">
                    <div class="leader-score-val">Lvl ${leader.level}</div>
                    <div class="leader-score-lbl">${leader.xp} XP</div>
                </div>
            `;
            list.appendChild(row);
        });
        
        if (data.leaderboard.length === 0) {
            list.innerHTML = '<div class="no-data">Hozircha o\'yinchilar yo\'q.</div>';
        }
        
    } catch (e) {
        console.error(e);
    }
}

// Buy Item API Call
async function buyItem(itemKey) {
    try {
        const response = await fetch('/api/buy', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, item_key: itemKey })
        });
        
        const resData = await response.json();
        
        if (response.ok) {
            tg.showAlert(`🎉 ${resData.message}`);
            loadProfile();
        } else {
            tg.showAlert(`⚠️ ${resData.error || "Xatolik yuz berdi"}`);
        }
    } catch (e) {
        console.error(e);
        tg.showAlert("⚠️ Serverga ulanishda xato!");
    }
}

// Activate Shield API Call
async function activateShield() {
    try {
        const response = await fetch('/api/activate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, item_key: 'shield' })
        });
        
        const resData = await response.json();
        
        if (response.ok) {
            tg.showAlert("🛡️ Qalqon faollashtirildi!");
            loadProfile();
        } else {
            tg.showAlert(`⚠️ ${resData.error}`);
        }
    } catch (e) {
        console.error(e);
    }
}

// Attach event listeners to buy buttons
document.querySelectorAll('.btn-buy').forEach(btn => {
    btn.addEventListener('click', () => {
        const itemKey = btn.getAttribute('data-item');
        buyItem(itemKey);
    });
});

// Dynamic Role Calculator
let calculatorInitialized = false;

function initCalculator() {
    if (calculatorInitialized) return;
    
    const slider = document.getElementById('player-slider');
    const countDisplay = document.getElementById('calc-player-count');
    
    slider.addEventListener('input', () => {
        const count = parseInt(slider.value);
        countDisplay.innerText = count;
        updateCalculator(count);
    });
    
    // Initial update
    updateCalculator(parseInt(slider.value));
    calculatorInitialized = true;
}

function updateCalculator(playerCount) {
    const list = document.getElementById('calc-roles-list');
    list.innerHTML = '';
    
    // Exact logic from game/loop.py
    let roles = [];
    if (playerCount < 5) {
        roles = ["Mafia", "Doctor", "Detective", "Civilian", "Civilian"];
    } else if (playerCount === 5) {
        roles = ["Mafia", "Doctor", "Detective", "Civilian", "Civilian"];
    } else if (playerCount === 6) {
        roles = ["Mafia", "Don", "Doctor", "Detective", "Civilian", "Civilian"];
    } else if (playerCount === 7) {
        roles = ["Mafia", "Don", "Doctor", "Detective", "Bodyguard", "Civilian", "Civilian"];
    } else if (playerCount === 8) {
        roles = ["Mafia", "Mafia", "Don", "Doctor", "Detective", "Bodyguard", "Civilian", "Civilian"];
    } else if (playerCount === 9) {
        roles = ["Mafia", "Mafia", "Don", "Doctor", "Detective", "Bodyguard", "Courtesan", "Civilian", "Civilian"];
    } else if (playerCount >= 10 && playerCount < 15) {
        roles = ["Mafia", "Mafia", "Don", "Maniac", "Doctor", "Detective", "Bodyguard", "Courtesan", "Civilian", "Civilian"];
        while (roles.length < playerCount) {
            roles.push("Civilian");
        }
    } else { // 15+
        roles = ["Mafia", "Mafia", "Mafia", "Don", "Maniac", "Doctor", "Detective", "Bodyguard", "Courtesan", "Civilian", "Civilian", "Civilian", "Civilian", "Civilian", "Civilian"];
        while (roles.length < playerCount) {
            roles.push("Civilian");
        }
    }
    
    // Count occurrences
    const roleCounts = {};
    roles.forEach(r => {
        roleCounts[r] = (roleCounts[r] || 0) + 1;
    });
    
    const roleEmojis = {
        "Mafia": "🔴",
        "Don": "🕶️",
        "Civilian": "🟢",
        "Detective": "🔵",
        "Doctor": "🟡",
        "Bodyguard": "🛡️",
        "Courtesan": "🌸",
        "Maniac": "🦹"
    };
    
    const roleUzNames = {
        "Mafia": "Mafiya",
        "Don": "Don (Boshliq)",
        "Civilian": "Tinch aholi",
        "Detective": "Komissar (Detective)",
        "Doctor": "Shifokor",
        "Bodyguard": "Tansoqchi",
        "Courtesan": "Kutizanka",
        "Maniac": "Telba (Maniac)"
    };
    
    for (let r in roleCounts) {
        const item = document.createElement('div');
        item.className = 'calc-role-item';
        
        const count = roleCounts[r];
        const emoji = roleEmojis[r] || "🎭";
        const name = roleUzNames[r] || r;
        
        item.innerHTML = `
            <div style="display:flex; align-items:center; gap:10px;">
                <span style="font-size:1.3rem;">${emoji}</span>
                <span style="font-weight:600; font-size:0.9rem;">${name}</span>
            </div>
            <span style="font-weight:800; color:var(--primary); font-size:0.95rem;">${count} ta</span>
        `;
        list.appendChild(item);
    }
}

// Initial load
loadProfile();
loadActiveGame();

// Poll active game status every 4 seconds
setInterval(loadActiveGame, 4000);

// Active Game Arena Actions
// Active Game Arena Actions
async function loadActiveGame() {
    try {
        const response = await fetch(`/api/game/status?user_id=${userId}`);
        if (!response.ok) throw new Error("Game status fetch failed");
        
        const data = await response.json();
        const lobbyView = document.getElementById('match-lobby-view');
        const roomLobbyView = document.getElementById('match-room-lobby-view');
        const gameView = document.getElementById('match-active-game-view');
        
        if (!data.inGame) {
            lobbyView.style.display = 'block';
            roomLobbyView.style.display = 'none';
            gameView.style.display = 'none';
            loadPartyStatus();
            loadPublicRoomsList();
            return;
        }
        
        currentRoomId = data.room_id;
        
        // Waiting room lobby (phase === 'lobby')
        if (data.phase === "lobby") {
            lobbyView.style.display = 'none';
            roomLobbyView.style.display = 'block';
            gameView.style.display = 'none';
            
            document.getElementById('lobby-room-title').innerText = `XONA #${data.room_id}`;
            const container = document.getElementById('lobby-players-container');
            container.innerHTML = data.players.map((p, idx) => `
                <div style="padding:8px 12px; background:rgba(255,255,255,0.02); border:1px solid rgba(255,255,255,0.05); border-radius:8px; display:flex; justify-content:space-between; align-items:center; margin-bottom: 4px;">
                    <span style="font-size:13px; color:#fff;">${idx+1}. 👤 <strong>${p.name}</strong></span>
                    ${p.user_id === data.owner_id ? '<span style="font-size:10px; color:#ffc439; background:rgba(255,196,57,0.1); padding:2px 6px; border-radius:6px; font-weight:bold;">👑 Ega</span>' : ''}
                </div>
            `).join('');
            
            const startBtn = document.getElementById('btn-lobby-start');
            if (data.owner_id === userId) {
                startBtn.style.display = 'inline-block';
                startBtn.disabled = data.players.length < 5;
            } else {
                startBtn.style.display = 'none';
            }
            return;
        }
        
        // Active game!
        lobbyView.style.display = 'none';
        roomLobbyView.style.display = 'none';
        gameView.style.display = 'block';
        
        // Render phase
        const phaseBadge = document.getElementById('game-phase-badge');
        const phaseNames = {
            "night": "🌙 TUN",
            "day": "🌅 KUN",
            "voting": "🗳️ OVOZ BERISH",
            "ended": "🏁 YAKUNLANDI"
        };
        phaseBadge.innerText = phaseNames[data.phase] || data.phase.toUpperCase();
        
        // Render my role
        const roleEmojis = {
            "Mafia": "🔴", "Don": "🕶️", "Civilian": "🟢", "Detective": "🔵",
            "Doctor": "🟡", "Bodyguard": "🛡️", "Courtesan": "🌸", "Maniac": "🦹"
        };
        const myRoleText = document.getElementById('game-my-role');
        myRoleText.innerText = `${roleEmojis[data.myRole] || "🎭"} ${data.myRole}`;
        
        // Render status instructions
        const statusText = document.getElementById('game-status-text');
        if (!data.isAlive) {
            statusText.innerText = "💀 Siz o'ldirildingiz. O'yinni kuzatib boring.";
        } else if (data.phase === "night") {
            const instructions = {
                "Mafia": "Sheriklaringiz bilan kimnidir o'ldirish uchun ovoz bering.",
                "Don": "Komissarni topish uchun o'yinchilardan birini tekshiring.",
                "Detective": "Gumondorning rolini tekshiring yoki uni otib yuboring.",
                "Doctor": "Tunda kimnidir o'limdan qutqarish uchun davolang.",
                "Bodyguard": "Tunda kimnidir himoya qiling (u o'rniga o'lasiz).",
                "Courtesan": "Birorta o'yinchining tungi qobiliyatini bloklang.",
                "Maniac": "Tunda o'ldirish uchun birorta qurbonni tanlang.",
                "Civilian": "Tunda tinch aholi uxlamoqda... Tong otishini kuting."
            };
            statusText.innerText = instructions[data.myRole] || "Tunda harakat qiling.";
        } else if (data.phase === "voting") {
            statusText.innerText = "🗳️ Munozara tugadi. Kimni osmoqchisiz? Ovoz bering!";
        } else {
            statusText.innerText = "🌅 Darktown shahri uyg'ondi. Guruhda gaplashing va gumondorlarni aniqlang.";
        }
        
        // Render players grid
        const grid = document.getElementById('game-players-grid');
        grid.innerHTML = '';
        
        data.players.forEach(p => {
            const card = document.createElement('div');
            card.className = `game-player-card ${p.is_alive ? 'alive' : 'dead'}`;
            
            // Left section: status dot + name + revealed role
            const roleReveal = p.role ? `<span class="player-card-role-reveal">${roleEmojis[p.role] || ""} ${p.role}</span>` : '';
            card.innerHTML = `
                <div class="player-card-left">
                    <span class="player-card-status ${p.is_alive ? 'alive' : 'dead'}"></span>
                    <span class="player-card-name">${p.name} ${p.user_id === userId ? "(Siz)" : ""}</span>
                    ${roleReveal}
                </div>
            `;
            
            // Actions section (if user is alive and target is alive)
            if (data.isAlive && p.is_alive && p.user_id !== userId) {
                const actionsContainer = document.createElement('div');
                actionsContainer.className = 'player-card-actions';
                
                if (data.phase === "night") {
                    if (data.myRole === "Mafia" || data.myRole === "Don") {
                        if (p.role !== "Mafia" && p.role !== "Don") {
                            addActionBtn(actionsContainer, "🔴 O'ldirish", () => sendAction(p.user_id, "mafia"), "shoot");
                        }
                    }
                    if (data.myRole === "Don") {
                        addActionBtn(actionsContainer, "🔍 Tekshirish", () => sendAction(p.user_id, "don"), "check");
                    }
                    if (data.myRole === "Detective") {
                        addActionBtn(actionsContainer, "🔍 Tekshirish", () => sendAction(p.user_id, "det_check"), "check");
                        addActionBtn(actionsContainer, "🔫 Otish", () => sendAction(p.user_id, "det_shoot"), "shoot");
                    }
                    if (data.myRole === "Doctor") {
                        addActionBtn(actionsContainer, "🏥 Davolash", () => sendAction(p.user_id, "doctor"), "heal");
                    }
                    if (data.myRole === "Bodyguard") {
                        addActionBtn(actionsContainer, "🛡️ Himoya", () => sendAction(p.user_id, "bodyguard"), "guard");
                    }
                    if (data.myRole === "Courtesan") {
                        addActionBtn(actionsContainer, "🌸 Bloklash", () => sendAction(p.user_id, "courtesan"), "block");
                    }
                    if (data.myRole === "Maniac") {
                        addActionBtn(actionsContainer, "🔴 O'ldirish", () => sendAction(p.user_id, "maniac"), "shoot");
                    }
                } else if (data.phase === "voting") {
                    addActionBtn(actionsContainer, "🗳️ Ovoz", () => sendVote(p.user_id), "vote");
                }
                
                card.appendChild(actionsContainer);
            }
            
            grid.appendChild(card);
        });
        
        // Add skip voting button if voting phase
        if (data.isAlive && data.phase === "voting") {
            const skipCard = document.createElement('div');
            skipCard.className = 'game-player-card';
            skipCard.innerHTML = `
                <div class="player-card-left">
                    <span class="player-card-name">⏩ Hech kimga ovoz bermaslik</span>
                </div>
            `;
            const actionsContainer = document.createElement('div');
            actionsContainer.className = 'player-card-actions';
            addActionBtn(actionsContainer, "⏩ Ovoz", () => sendVote("skip"), "vote");
            skipCard.appendChild(actionsContainer);
            grid.appendChild(skipCard);
        }
        
        // Live room chat for Day/Discussion phase in Room games
        const dayChatSection = document.getElementById('room-day-chat-section');
        if (data.room_id && data.isAlive && (data.phase === 'day' || data.phase === 'discussion')) {
            dayChatSection.style.display = 'block';
            loadRoomDayChatMessages();
        } else {
            dayChatSection.style.display = 'none';
        }
        
        // Render game logs
        const logsDiv = document.getElementById('game-logs');
        if (data.logs && data.logs.length > 0) {
            logsDiv.innerHTML = data.logs.map(log => `<div>${log}</div>`).join('');
            logsDiv.scrollTop = logsDiv.scrollHeight;
        } else {
            logsDiv.innerHTML = `<div style="color:var(--text-muted); text-align:center;">${currentLang === 'ru' ? 'Событий пока нет.' : currentLang === 'en' ? 'No events yet.' : currentLang === 'kz' ? 'Әзірге оқиғалар жоқ.' : 'Hozircha voqealar yo\'q.'}</div>`;
        }
        
        // Render ghost chat
        const ghostChatSection = document.getElementById('ghost-chat-section');
        if (!data.isAlive) {
            ghostChatSection.style.display = 'block';
            loadGhostChatMessages();
        } else {
            ghostChatSection.style.display = 'none';
        }
        
    } catch (e) {
        console.error("Active game fetch error:", e);
    }
}

// Party Management functions
async function loadPartyStatus() {
    try {
        const response = await fetch(`/api/party/status?user_id=${userId}`);
        const data = await response.json();
        
        const badge = document.getElementById('party-status-badge');
        const info = document.getElementById('party-info-area');
        const list = document.getElementById('party-members-list');
        const createBtn = document.getElementById('btn-create-party');
        const copyBtn = document.getElementById('btn-copy-party-link');
        const leaveBtn = document.getElementById('btn-leave-party');
        
        if (data.inParty) {
            currentPartyId = data.party_id;
            badge.innerText = data.isLeader ? "👑 LIDER" : "👥 AZO";
            badge.style.color = data.isLeader ? "#ffc439" : "#00f2fe";
            
            info.innerText = `Partiya ID: ${data.party_id.replace('party_', '')}`;
            list.style.display = 'flex';
            list.innerHTML = data.members.map((m, idx) => `
                <div style="font-size:12px; display:flex; justify-content:space-between; margin-bottom:3px; color:#fff;">
                    <span>${idx+1}. 👤 ${m.first_name} (Lvl ${m.level})</span>
                    ${m.user_id === data.leader_id ? '<span style="font-size:9px; color:#ffc439; font-weight:bold;">👑 Lider</span>' : ''}
                </div>
            `).join('');
            
            createBtn.style.display = 'none';
            copyBtn.style.display = data.isLeader ? 'inline-block' : 'none';
            leaveBtn.style.display = 'inline-block';
        } else {
            currentPartyId = null;
            badge.innerText = "Yakka (Solo)";
            badge.style.color = "#94a3b8";
            info.innerText = "Siz hozircha guruhda emassiz. Do'stlaringiz bilan birga o'ynash uchun partiya yarating.";
            list.style.display = 'none';
            
            createBtn.style.display = 'inline-block';
            copyBtn.style.display = 'none';
            leaveBtn.style.display = 'none';
        }
    } catch(e) {
        console.error(e);
    }
}

async function createParty() {
    try {
        const response = await fetch('/api/party/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId })
        });
        const data = await response.json();
        if (data.success) {
            loadPartyStatus();
        } else {
            alert(data.error);
        }
    } catch(e) {
        console.error(e);
    }
}

async function leaveParty() {
    if (!currentPartyId) return;
    try {
        const response = await fetch('/api/party/leave', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, party_id: currentPartyId })
        });
        const data = await response.json();
        if (data.success) {
            loadPartyStatus();
        } else {
            alert(data.error);
        }
    } catch(e) {
        console.error(e);
    }
}

function copyPartyLink() {
    if (!currentPartyId) return;
    const link = `https://t.me/darktownuz_bot?start=${currentPartyId}`;
    navigator.clipboard.writeText(link).then(() => {
        alert("Taklif havolasi nusxalandi!");
    }).catch(() => {
        alert(link);
    });
}

// Matchmaking and Room custom creation
async function autoMatchmaking() {
    try {
        // Query public rooms first
        const response = await fetch('/api/rooms/list');
        const data = await response.json();
        
        if (data.rooms && data.rooms.length > 0) {
            // Join the first open public room
            const firstRoom = data.rooms[0];
            const joinRes = await fetch('/api/rooms/join', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: userId, room_id: firstRoom.room_id })
            });
            const joinData = await joinRes.json();
            if (joinData.success) {
                loadActiveGame();
                return;
            }
        }
        
        // No open room found, automatically create one
        const createRes = await fetch('/api/rooms/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, is_private: 0, pin_code: "", day_limit: 60, night_limit: 60 })
        });
        const createData = await createRes.json();
        if (createData.success) {
            loadActiveGame();
        } else {
            alert(createData.error);
        }
    } catch(e) {
        console.error(e);
    }
}

async function submitCreateRoom() {
    const isPrivate = document.getElementById('room-is-private').checked ? 1 : 0;
    const pinCode = document.getElementById('room-pin-code').value.trim();
    const dayLimit = parseInt(document.getElementById('room-day-limit').value) || 60;
    const nightLimit = parseInt(document.getElementById('room-night-limit').value) || 60;
    
    try {
        const response = await fetch('/api/rooms/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, is_private: isPrivate, pin_code: pinCode, day_limit: dayLimit, night_limit: nightLimit })
        });
        const data = await response.json();
        if (data.success) {
            document.getElementById('room-create-opts').style.display = 'none';
            loadActiveGame();
        } else {
            alert(data.error);
        }
    } catch(e) {
        console.error(e);
    }
}

async function submitJoinRoom() {
    const roomIdInput = document.getElementById('join-room-id');
    const roomPinInput = document.getElementById('join-room-pin');
    
    const roomId = roomIdInput.value.trim();
    const pin = roomPinInput.value.trim();
    
    if (!roomId) {
        alert("Xona ID raqami kiritilishi shart!");
        return;
    }
    
    try {
        const response = await fetch('/api/rooms/join', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, room_id: roomId, pin_code: pin })
        });
        const data = await response.json();
        if (data.success) {
            roomIdInput.value = '';
            roomPinInput.value = '';
            loadActiveGame();
        } else {
            alert(data.error);
        }
    } catch(e) {
        console.error(e);
    }
}

async function leaveRoom() {
    if (!currentRoomId) return;
    try {
        const response = await fetch('/api/rooms/leave', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, room_id: currentRoomId })
        });
        const data = await response.json();
        if (data.success) {
            currentRoomId = null;
            loadActiveGame();
        } else {
            alert(data.error);
        }
    } catch(e) {
        console.error(e);
    }
}

async function startRoom() {
    if (!currentRoomId) return;
    try {
        const response = await fetch('/api/rooms/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, room_id: currentRoomId })
        });
        const data = await response.json();
        if (data.success) {
            loadActiveGame();
        } else {
            alert(data.error);
        }
    } catch(e) {
        console.error(e);
    }
}

async function loadPublicRoomsList() {
    try {
        const response = await fetch('/api/rooms/list');
        const data = await response.json();
        
        const container = document.getElementById('active-rooms-list');
        if (data.rooms && data.rooms.length > 0) {
            container.innerHTML = data.rooms.map(room => `
                <div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.05); padding:12px; border-radius:12px; display:flex; justify-content:space-between; align-items:center; text-align:left; margin-bottom: 4px;">
                    <div>
                        <div style="font-weight:bold; font-size:13px; color:#00f2fe;">Xona #${room.room_id}</div>
                        <div style="font-size:10px; color:#94a3b8; margin-top:2px;">O'yinchilar: ${room.player_count} ta • Kun: ${room.day_limit}s / Tun: ${room.night_limit}s</div>
                    </div>
                    <button class="btn btn-sm btn-primary" onclick="directJoinRoom('${room.room_id}')" style="font-size:11px; padding:4px 10px; height:auto; line-height:1;">Qo'shilish</button>
                </div>
            `).join('');
        } else {
            container.innerHTML = `
                <div style="font-size:12px; color:#94a3b8; padding:20px; background:rgba(255,255,255,0.01); border-radius:12px; border:1px dashed rgba(255,255,255,0.05); text-align:center;">
                    Hozircha ochiq lobbilar yo'q. Avto matching orqali birinchilardan bo'lib yarating!
                </div>
            `;
        }
    } catch(e) {
        console.error(e);
    }
}

window.directJoinRoom = async function(roomId) {
    try {
        const response = await fetch('/api/rooms/join', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, room_id: roomId })
        });
        const data = await response.json();
        if (data.success) {
            loadActiveGame();
        } else {
            alert(data.error);
        }
    } catch(e) {
        console.error(e);
    }
};

// Day chat messages inside room
async function loadRoomDayChatMessages() {
    try {
        const response = await fetch(`/api/rooms/chat/messages?user_id=${userId}`);
        const data = await response.json();
        
        const container = document.getElementById('room-day-messages');
        container.innerHTML = '';
        if (data.messages && data.messages.length > 0) {
            data.messages.forEach(msg => {
                const isMine = msg.sender_id === userId;
                const bubble = document.createElement('div');
                bubble.className = `chat-msg ${isMine ? 'mine' : ''}`;
                bubble.innerHTML = `
                    <div class="chat-sender">${msg.sender}</div>
                    <div class="chat-text">${msg.text}</div>
                    <div class="chat-time">${msg.timestamp}</div>
                `;
                container.appendChild(bubble);
            });
            container.scrollTop = container.scrollHeight;
        } else {
            container.innerHTML = `<div style="color:#64748b; text-align:center; margin-top:30px; font-size:12px;">Munozara chati bo'sh. Qotilni aniqlash uchun yozing!</div>`;
        }
    } catch(e) {
        console.error(e);
    }
}

async function sendRoomDayChatMessage() {
    const input = document.getElementById('room-day-chat-input');
    const text = input.value.trim();
    if (!text) return;
    
    try {
        const response = await fetch('/api/rooms/chat/send', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, text: text })
        });
        const data = await response.json();
        if (data.success) {
            input.value = '';
            loadRoomDayChatMessages();
        } else {
            alert(data.error);
        }
    } catch(e) {
        console.error(e);
    }
}

function addActionBtn(container, text, onClick, className) {
    const btn = document.createElement('button');
    btn.className = `action-btn-mini ${className}`;
    btn.innerText = text;
    btn.onclick = onClick;
    container.appendChild(btn);
}

async function sendAction(targetId, actionType) {
    try {
        const response = await fetch('/api/game/action', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: userId,
                target_id: targetId,
                action_type: actionType
            })
        });
        const data = await response.json();
        if (data.success) {
            alert(`✅ ${data.message}`);
            loadActiveGame();
        } else {
            alert(`⚠️ Xato: ${data.error}`);
        }
    } catch (e) {
        console.error(e);
        alert("Server bilan aloqada xatolik!");
    }
}

async function sendVote(targetId) {
    try {
        const response = await fetch('/api/game/vote', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: userId,
                target_id: targetId
            })
        });
        const data = await response.json();
        if (data.success) {
            alert(`🗳️ ${data.message}`);
            loadActiveGame();
        } else {
            alert(`⚠️ Xato: ${data.error}`);
        }
    } catch (e) {
        console.error(e);
        alert("Server bilan aloqada xatolik!");
    }
}

// Admin Tab Actions
async function loadAdminStats() {
    try {
        const response = await fetch(`/api/admin/stats?admin_id=${userId}`);
        if (!response.ok) throw new Error("Admin stats fetch failed");
        
        const data = await response.json();
        if (data.success) {
            document.getElementById('admin-total-users').innerText = data.total_users;
            document.getElementById('admin-total-plays').innerText = data.total_plays;
            document.getElementById('admin-active-games').innerText = data.active_games;
        }
    } catch (e) {
        console.error("Admin stats error:", e);
    }
}

document.getElementById('admin-submit-btn').addEventListener('click', async () => {
    const targetIdInput = document.getElementById('admin-target-id');
    const coinsInput = document.getElementById('admin-give-coins');
    const xpInput = document.getElementById('admin-give-xp');
    
    const targetId = parseInt(targetIdInput.value);
    const coins = parseInt(coinsInput.value) || 0;
    const xp = parseInt(xpInput.value) || 0;
    
    if (!targetId) {
        alert("Foydalanuvchi Telegram ID kiritilishi shart!");
        return;
    }
    
    try {
        const response = await fetch('/api/admin/give', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                admin_id: userId,
                target_id: targetId,
                coins: coins,
                xp: xp
            })
        });
        
        const resData = await response.json();
        if (resData.success) {
            alert(`✅ Muvaffaqiyatli bajarildi! Foydalanuvchi ${targetId} balansiga ${coins} tanga va ${xp} XP yuborildi.`);
            targetIdInput.value = '';
            coinsInput.value = '0';
            xpInput.value = '0';
            loadAdminStats(); // Refresh stats
        } else {
            alert(`⚠️ Xato: ${resData.error}`);
        }
    } catch (e) {
        console.error("Admin action failed:", e);
        alert("Server bilan aloqada xatolik!");
    }
});

// Localization system
let currentLang = "uz";

const LOCALES = {
    uz: {
        "title_profile": "👤 Profil",
        "lbl_games": "O'yinlar",
        "lbl_wins": "G'alabalar",
        "lbl_win_rate": "Yutuq Foizi",
        "lbl_shield_active": "Faol (tajriba himoyalangan)",
        "lbl_shield_inactive": "Faol emas",
        "lbl_no_data": "Hozircha o'yinlar o'ynalmagan.",
        "lbl_buy_coins": "🪙 Tanga sotib olish",
        "lbl_inventory": "Sizning Inventaringiz",
        "lbl_daily_claim": "Kunlik Bonus",
        "lbl_daily_claim_time": "Hozir olish",
        "lbl_ref_title": "👥 Taklifnoma Tizimi",
        "lbl_ref_desc": "Do'stlaringizni taklif qiling va har biri uchun +50 tanga bonus oling!",
        "btn_copy_ref": "Havolani nusxalash",
        "lbl_achievements_title": "Erishilgan Yutuqlar",
        "lbl_stats_title": "O'yin Statistikasi",
        "lbl_ghost_chat_title": "👻 Arvoxlar Chati (Ghost Chat)",
        "lbl_game_logs_title": "📜 O'yin voqealari",
        "lbl_players_title": "👥 O'yinchilar maydoni",
        "msg_copied": "Havola buferga nusxalandi!",
        "msg_already_claimed": "Kunlik bonus allaqachon olingan!",
        "btn_buy": "Sotib olish",
        "btn_activate": "Faollashtirish",
        "calc_title": "🎮 Mafiya Balans Kalkulyatori",
        "calc_lbl_players": "O'yinchilar soni",
        "calc_roles_distribution": "👥 Kutilayotgan rollar taqsimoti",
        "calc_roles_guide": "🎭 Rol qoidalari va tavsiflari",
        "nav_profile": "Profil",
        "nav_shop": "Do'kon",
        "nav_leaderboard": "Reyting",
        "nav_match": "O'yin",
        "nav_admin": "Admin",
        "lbl_shop": "Darktown Do'koni",
        "lbl_leaderboard_title": "Global Top O'yinchilar",
        "shop_shield_name": "XP Qalqoni",
        "shop_shield_desc": "Yutqazganingizda XP yo'qotishdan himoya qiladi (1 martalik).",
        "shop_mafia_name": "Mafiya Booster",
        "shop_mafia_desc": "Keyingi o'yinda Mafiya rolini olish imkoniyatini oshiradi.",
        "shop_det_name": "Komissar Booster",
        "shop_det_desc": "Keyingi o'yinda Komissar rolini olish imkoniyatini oshiradi.",
        "shop_doc_name": "Shifokor Booster",
        "shop_doc_desc": "Keyingi o'yinda Shifokor rolini olish imkoniyatini oshiradi.",
        "shop_maniac_name": "Telba Booster",
        "shop_maniac_desc": "Keyingi o'yinda Telba (Maniac) rolini olish imkoniyatini oshiradi.",
        "coin_pack_desc": "Mini App do'koni uchun {count} tanga.",
        "btn_pay_stars": "⭐️ Telegram Stars",
        "btn_pay_card": "💳 Visa / PayPal"
    },
    ru: {
        "title_profile": "👤 Профиль",
        "lbl_games": "Игры",
        "lbl_wins": "Победы",
        "lbl_win_rate": "Процент побед",
        "lbl_shield_active": "Активен (опыт защищен)",
        "lbl_shield_inactive": "Не активен",
        "lbl_no_data": "Игр пока нет.",
        "lbl_buy_coins": "🪙 Купить монеты",
        "lbl_inventory": "Ваш Инвентарь",
        "lbl_daily_claim": "Ежедневный Бонус",
        "lbl_daily_claim_time": "Забрать",
        "lbl_ref_title": "👥 Реферальная Система",
        "lbl_ref_desc": "Приглашайте друзей и получайте +50 монет за каждого!",
        "btn_copy_ref": "Копировать ссылку",
        "lbl_achievements_title": "Достижения",
        "lbl_stats_title": "Статистика Игры",
        "lbl_ghost_chat_title": "👻 Чат Призраков (Ghost Chat)",
        "lbl_game_logs_title": "📜 События игры",
        "lbl_players_title": "👥 Игровое поле",
        "msg_copied": "Ссылка скопирована в буфер!",
        "msg_already_claimed": "Ежедневный бонус уже получен!",
        "btn_buy": "Купить",
        "btn_activate": "Активировать",
        "calc_title": "🎮 Калькулятор Баланса Мафии",
        "calc_lbl_players": "Количество игроков",
        "calc_roles_distribution": "👥 Ожидаемое распределение ролей",
        "calc_roles_guide": "🎭 Правила и описание ролей",
        "nav_profile": "Профиль",
        "nav_shop": "Магазин",
        "nav_leaderboard": "Рейтинг",
        "nav_match": "Игра",
        "nav_admin": "Админ",
        "lbl_shop": "Магазин Darktown",
        "lbl_leaderboard_title": "Глобальный Топ Игроков",
        "shop_shield_name": "Щит XP",
        "shop_shield_desc": "Защищает от потери опыта при поражении (одноразовый).",
        "shop_mafia_name": "Бустер Мафии",
        "shop_mafia_desc": "Увеличивает шанс получить роль Мафии в следующей игре.",
        "shop_det_name": "Бустер Комиссара",
        "shop_det_desc": "Увеличивает шанс получить роль Комиссара в следующей игре.",
        "shop_doc_name": "Бустер Доктора",
        "shop_doc_desc": "Увеличивает шанс получить роль Доктора в следующей игре.",
        "shop_maniac_name": "Бустер Маньяка",
        "shop_maniac_desc": "Увеличивает шанс получить роль Маньяка в следующей игре.",
        "coin_pack_desc": "Для покупок в магазине {count} монет.",
        "btn_pay_stars": "⭐️ Telegram Stars",
        "btn_pay_card": "💳 Visa / PayPal"
    },
    en: {
        "title_profile": "👤 Profile",
        "lbl_games": "Games",
        "lbl_wins": "Wins",
        "lbl_win_rate": "Win Rate",
        "lbl_shield_active": "Active (XP protected)",
        "lbl_shield_inactive": "Inactive",
        "lbl_no_data": "No games played yet.",
        "lbl_buy_coins": "🪙 Buy Coins",
        "lbl_inventory": "Your Inventory",
        "lbl_daily_claim": "Daily Reward",
        "lbl_daily_claim_time": "Claim Now",
        "lbl_ref_title": "👥 Referral Program",
        "lbl_ref_desc": "Invite friends and get +50 coins for each referral!",
        "btn_copy_ref": "Copy Invite Link",
        "lbl_achievements_title": "Achievements",
        "lbl_stats_title": "Game Stats",
        "lbl_ghost_chat_title": "👻 Ghost Chat",
        "lbl_game_logs_title": "📜 Game events",
        "lbl_players_title": "👥 Player Field",
        "msg_copied": "Link copied to clipboard!",
        "msg_already_claimed": "Daily reward already claimed!",
        "btn_buy": "Buy",
        "btn_activate": "Activate",
        "calc_title": "🎮 Mafia Balance Calculator",
        "calc_lbl_players": "Number of players",
        "calc_roles_distribution": "👥 Expected Role Distribution",
        "calc_roles_guide": "🎭 Role Rules & Descriptions",
        "nav_profile": "Profile",
        "nav_shop": "Shop",
        "nav_leaderboard": "Leaderboard",
        "nav_match": "Play",
        "nav_admin": "Admin",
        "lbl_shop": "Darktown Shop",
        "lbl_leaderboard_title": "Global Top Players",
        "shop_shield_name": "XP Shield",
        "shop_shield_desc": "Protects from losing XP when you lose (1-time use).",
        "shop_mafia_name": "Mafia Booster",
        "shop_mafia_desc": "Increases the chance of getting the Mafia role in the next game.",
        "shop_det_name": "Detective Booster",
        "shop_det_desc": "Increases the chance of getting the Detective role in the next game.",
        "shop_doc_name": "Doctor Booster",
        "shop_doc_desc": "Increases the chance of getting the Doctor role in the next game.",
        "shop_maniac_name": "Maniac Booster",
        "shop_maniac_desc": "Increases the chance of getting the Maniac role in the next game.",
        "coin_pack_desc": "Get {count} coins for the Mini App shop.",
        "btn_pay_stars": "⭐️ Telegram Stars",
        "btn_pay_card": "💳 Visa / PayPal"
    },
    kz: {
        "title_profile": "👤 Профиль",
        "lbl_games": "Ойындар",
        "lbl_wins": "Жеңістер",
        "lbl_win_rate": "Жеңіс Пайызы",
        "lbl_shield_active": "Белсенді (XP қорғалған)",
        "lbl_shield_inactive": "Белсенді емес",
        "lbl_no_data": "Әзірге ойындар жоқ.",
        "lbl_buy_coins": "🪙 Монета сатып алу",
        "lbl_inventory": "Сіздің Инвентарыңыз",
        "lbl_daily_claim": "Күнделікті Бонус",
        "lbl_daily_claim_time": "Қазір алу",
        "lbl_ref_title": "👥 Шақыру Жүйесі",
        "lbl_ref_desc": "Достарыңызды шақырыңыз және әрқайсысы үшін +50 монета алыңыз!",
        "btn_copy_ref": "Сілтемені Көшіру",
        "lbl_achievements_title": "Қол Жеткізілген Жетістіктер",
        "lbl_stats_title": "Ойын Статистикасы",
        "lbl_ghost_chat_title": "👻 Елестер Чаттары (Ghost Chat)",
        "lbl_game_logs_title": "📜 Ойын оқиғалары",
        "lbl_players_title": "👥 Ойыншылар алаңы",
        "msg_copied": "Сілтеме көшірілді!",
        "msg_already_claimed": "Күнделікті бонус алынған!",
        "btn_buy": "Сатып алу",
        "btn_activate": "Белсендіру",
        "calc_title": "🎮 Мафия Баланс Калькуляторы",
        "calc_lbl_players": "Ойыншылар саны",
        "calc_roles_distribution": "👥 Күтілетін рөлдерді бөлу",
        "calc_roles_guide": "🎭 Рөлдердің ережелері мен сипаттамасы",
        "nav_profile": "Профиль",
        "nav_shop": "Дүкен",
        "nav_leaderboard": "Рейтинг",
        "nav_match": "Ойын",
        "nav_admin": "Админ",
        "lbl_shop": "Darktown Дүкені",
        "lbl_leaderboard_title": "Глобалды Үздік Ойыншылар",
        "shop_shield_name": "XP Қалқаны",
        "shop_shield_desc": "Ұтылған кезде тәжірибені (XP) жоғалтудан қорғайды (1 реттік).",
        "shop_mafia_name": "Мафия Бустері",
        "shop_mafia_desc": "Келесі ойында Мафия рөлін алу мүмкіндігін арттырады.",
        "shop_det_name": "Комиссар Бустерi",
        "shop_det_desc": "Келесі ойында Комиссар рөлін алу мүмкіндігін арттырады.",
        "shop_doc_name": "Дәрігер Бустерi",
        "shop_doc_desc": "Келесі ойында Дәрігер рөлін алу мүмкіндігін арттырады.",
        "shop_maniac_name": "Маньяк Бустерi",
        "shop_maniac_desc": "Келесі ойында Маньяк рөлін алу мүмкіндігін арттырады.",
        "coin_pack_desc": "Дүкен үшін {count} монета.",
        "btn_pay_stars": "⭐️ Telegram Stars",
        "btn_pay_card": "💳 Visa / PayPal"
    }
};

function t(key) {
    const group = LOCALES[currentLang] || LOCALES.uz;
    return group[key] || key;
}

function updateLang(lang) {
    if (!LOCALES[lang]) lang = "uz";
    currentLang = lang;
    
    // Update select element
    document.getElementById('select-lang').value = lang;
    
    // Update dropdown label text
    const langNames = { uz: "O'zbekcha", ru: "Русский", en: "English", kz: "Қазақша" };
    document.getElementById('lbl-profile-lang').innerText = "Til: " + langNames[lang];
    
    // Profile labels
    document.getElementById('lbl-daily-claim').innerText = t("lbl_daily_claim");
    document.getElementById('lbl-ref-title').innerText = t("lbl_ref_title");
    document.getElementById('lbl-ref-desc').innerText = t("lbl_ref_desc");
    document.getElementById('btn-copy-ref').innerText = t("btn_copy_ref");
    document.getElementById('lbl-achievements-title').innerText = t("lbl_achievements_title");
    document.getElementById('lbl-stats-title').innerText = t("lbl_stats_title");
    document.getElementById('lbl-inventory-title').innerText = t("lbl_inventory");
    document.getElementById('lbl-buy-coins-title').innerText = t("lbl_buy_coins");
    
    // Game Arena labels
    document.getElementById('lbl-players-title').innerText = t("lbl_players_title");
    document.getElementById('lbl-game-logs-title').innerText = t("lbl_game_logs_title");
    document.getElementById('lbl-ghost-chat-title').innerText = t("lbl_ghost_chat_title");
    
    // Bottom nav bar labels
    document.getElementById('nav-lbl-profile').innerText = t("nav_profile");
    document.getElementById('nav-lbl-shop').innerText = t("nav_shop");
    document.getElementById('nav-lbl-leaderboard').innerText = t("nav_leaderboard");
    document.getElementById('nav-lbl-match').innerText = t("nav_match");
    if (document.getElementById('nav-lbl-admin')) {
        document.getElementById('nav-lbl-admin').innerText = t("nav_admin");
    }
    
    // Shop labels
    document.getElementById('lbl-shop-title').innerText = t("lbl_shop");
    document.getElementById('shop-item-shield-name').innerText = t("shop_shield_name");
    document.getElementById('shop-item-shield-desc').innerText = t("shop_shield_desc");
    document.getElementById('shop-item-shield-btn').innerText = t("btn_buy");
    
    document.getElementById('shop-item-mafia-name').innerText = t("shop_mafia_name");
    document.getElementById('shop-item-mafia-desc').innerText = t("shop_mafia_desc");
    document.getElementById('shop-item-mafia-btn').innerText = t("btn_buy");
    
    document.getElementById('shop-item-det-name').innerText = t("shop_det_name");
    document.getElementById('shop-item-det-desc').innerText = t("shop_det_desc");
    document.getElementById('shop-item-det-btn').innerText = t("btn_buy");
    
    document.getElementById('shop-item-doc-name').innerText = t("shop_doc_name");
    document.getElementById('shop-item-doc-desc').innerText = t("shop_doc_desc");
    document.getElementById('shop-item-doc-btn').innerText = t("btn_buy");
    
    document.getElementById('shop-item-maniac-name').innerText = t("shop_maniac_name");
    document.getElementById('shop-item-maniac-desc').innerText = t("shop_maniac_desc");
    document.getElementById('shop-item-maniac-btn').innerText = t("btn_buy");
    
    // Coin packages
    document.getElementById('lbl-pack1-desc').innerText = t("coin_pack_desc").replace("{count}", "100");
    document.getElementById('lbl-pack2-desc').innerText = t("coin_pack_desc").replace("{count}", "500");
    document.getElementById('lbl-pack3-desc').innerText = t("coin_pack_desc").replace("{count}", "1000");
    
    // Payment buttons
    document.querySelectorAll('.btn-stars').forEach(btn => btn.innerText = t("btn_pay_stars"));
    document.querySelectorAll('.btn-card').forEach(btn => btn.innerText = t("btn_pay_card"));
    
    // Leaderboard title
    document.getElementById('lbl-leaderboard-title').innerText = t("lbl_leaderboard_title");
    
    // Calculator labels
    const calcTitle = document.querySelector('#match-calc-view .section-title');
    if (calcTitle) calcTitle.innerText = "🎮 " + t("calc_title");
}

function renderAchievements(stats, level) {
    const container = document.getElementById('achievements-container');
    container.innerHTML = '';
    
    // Check stats
    let totalWins = 0;
    let mafiaWins = 0;
    let detectiveWins = 0;
    let doctorWins = 0;
    let bodyguardWins = 0;
    let maniacWins = 0;
    
    if (stats && stats.length > 0) {
        stats.forEach(s => {
            totalWins += s.games_won;
            const role = s.role.toLowerCase();
            if (role === 'mafia' || role === 'don') mafiaWins += s.games_won;
            if (role === 'detective') detectiveWins += s.games_won;
            if (role === 'doctor') doctorWins += s.games_won;
            if (role === 'bodyguard') bodyguardWins += s.games_won;
            if (role === 'maniac') maniacWins += s.games_won;
        });
    }
    
    const achievements = [
        { id: "first_win", name: "Birinchi G'alaba", name_ru: "Первая Победа", name_en: "First Win", name_kz: "Бірінші Жеңіс", desc: "1 ta o'yinda g'alaba qozonish", desc_ru: "Выиграть 1 игру", desc_en: "Win 1 game", desc_kz: "1 ойында жеңіске жету", icon: "🏆", active: totalWins >= 1 },
        { id: "mafia_veteran", name: "Mafiya Veterani", name_ru: "Ветеран Мафии", name_en: "Mafia Veteran", name_kz: "Мафия Ардагері", desc: "Mafiya/Don sifatida 5 ta g'alaba", desc_ru: "5 побед за Мафию/Дона", desc_en: "5 wins as Mafia/Don", desc_kz: "Мафия/Дон ретінде 5 жеңіс", icon: "🕶️", active: mafiaWins >= 5 },
        { id: "detective_holmes", name: "Komissar Xolms", name_ru: "Комиссар Холмс", name_en: "Detective Holmes", name_kz: "Комиссар Холмс", desc: "Komissar sifatida 5 ta g'alaba", desc_ru: "5 побед за Комиссара", desc_en: "5 wins as Detective", desc_kz: "Комиссар ретінде 5 жеңіс", icon: "🔍", active: detectiveWins >= 5 },
        { id: "guardian_angel", name: "Himoyachi Farishta", name_ru: "Ангел-Хранитель", name_en: "Guardian Angel", name_kz: "Қорғаушы Періште", desc: "Shifokor/Tansoqchi sifatida 5 ta g'alaba", desc_ru: "5 побед за Доктора/Телохранителя", desc_en: "5 wins as Doctor/Bodyguard", desc_kz: "Дәрігер/Қорғаушы ретінде 5 жеңіс", icon: "👼", active: (doctorWins + bodyguardWins) >= 5 },
        { id: "serial_killer", name: "Telba Qotil", name_ru: "Безумный Убийца", name_en: "Maniac Killer", name_kz: "Жынды Қанішер", desc: "Telba sifatida 5 ta g'alaba", desc_ru: "5 побед за Маньяка", desc_en: "5 wins as Maniac", desc_kz: "Маньяк ретінде 5 жеңіс", icon: "🔪", active: maniacWins >= 5 },
        { id: "lvl_10", name: "Tajribali Jangchi", name_ru: "Опытный Боец", name_en: "Seasoned Fighter", name_kz: "Тәжірибелі Жауынгер", desc: "10-darajaga erishish", desc_ru: "Достичь 10 уровня", desc_en: "Reach Level 10", desc_kz: "10-деңгейге жету", icon: "🎖️", active: level >= 10 },
        { id: "lvl_100", name: "Afsonaviy Master", name_ru: "Легендарный Мастер", name_en: "Legendary Master", name_kz: "Аңызға айналған Шебер", desc: "100-darajaga erishish", desc_ru: "Достичь 100 уровня", desc_en: "Reach Level 100", desc_kz: "100-деңгейге жету", icon: "👑", active: level >= 100 }
    ];
    
    achievements.forEach(ach => {
        const item = document.createElement('div');
        item.className = 'achievement-badge';
        item.style.opacity = ach.active ? '1' : '0.35';
        item.style.filter = ach.active ? 'none' : 'grayscale(100%)';
        item.style.background = ach.active ? 'rgba(0, 242, 254, 0.1)' : 'rgba(255, 255, 255, 0.02)';
        item.style.border = ach.active ? '1px solid rgba(0, 242, 254, 0.3)' : '1px solid rgba(255, 255, 255, 0.05)';
        item.style.padding = '10px';
        item.style.borderRadius = '12px';
        item.style.minWidth = '110px';
        item.style.textAlign = 'center';
        item.style.fontSize = '11px';
        
        let display_name = ach.name;
        let display_desc = ach.desc;
        if (currentLang === 'ru') { display_name = ach.name_ru; display_desc = ach.desc_ru; }
        else if (currentLang === 'en') { display_name = ach.name_en; display_desc = ach.desc_en; }
        else if (currentLang === 'kz') { display_name = ach.name_kz; display_desc = ach.desc_kz; }
        
        item.innerHTML = `
            <div style="font-size:24px; margin-bottom:4px;">${ach.icon}</div>
            <div style="font-weight:bold; color:${ach.active ? '#fff' : '#94a3b8'}; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${display_name}</div>
            <div style="font-size:9px; color:#64748b; margin-top:2px;">${display_desc}</div>
        `;
        container.appendChild(item);
    });
}

function updateDailyClaimTimer(lastClaimTimestamp) {
    const claimTimeLabel = document.getElementById('lbl-daily-claim-time');
    const claimCard = document.getElementById('daily-claim-card');
    
    if (!lastClaimTimestamp) {
        claimTimeLabel.innerText = currentLang === 'ru' ? 'Получить' : currentLang === 'en' ? 'Claim' : currentLang === 'kz' ? 'Алу' : 'Hozir olish';
        claimTimeLabel.style.color = '#10b981';
        claimCard.style.pointerEvents = 'auto';
        claimCard.style.opacity = '1';
        return;
    }
    
    const lastClaim = new Date(lastClaimTimestamp);
    const now = new Date();
    const diffMs = now - lastClaim;
    const diffHrs = diffMs / (1000 * 60 * 60);
    
    if (diffHrs >= 24) {
        claimTimeLabel.innerText = currentLang === 'ru' ? 'Получить' : currentLang === 'en' ? 'Claim' : currentLang === 'kz' ? 'Алу' : 'Hozir olish';
        claimTimeLabel.style.color = '#10b981';
        claimCard.style.pointerEvents = 'auto';
        claimCard.style.opacity = '1';
    } else {
        const remainingMs = (24 * 60 * 60 * 1000) - diffMs;
        const hrs = Math.floor(remainingMs / (1000 * 60 * 60));
        const mins = Math.floor((remainingMs % (1000 * 60 * 60)) / (1000 * 60));
        
        let text = `${hrs}soat ${mins}min`;
        if (currentLang === 'ru') text = `Через ${hrs}ч ${mins}м`;
        else if (currentLang === 'en') text = `In ${hrs}h ${mins}m`;
        else if (currentLang === 'kz') text = `${hrs}с ${mins}м кейін`;
        
        claimTimeLabel.innerText = text;
        claimTimeLabel.style.color = '#94a3b8';
        claimCard.style.opacity = '0.6';
    }
}

async function loadGhostChatMessages() {
    try {
        const response = await fetch(`/api/game/ghost-chat/messages?user_id=${userId}`);
        if (!response.ok) throw new Error("Ghost messages fetch failed");
        const data = await response.json();
        
        const container = document.getElementById('ghost-messages');
        container.innerHTML = '';
        if (data.messages && data.messages.length > 0) {
            data.messages.forEach(msg => {
                const item = document.createElement('div');
                item.style.padding = '4px 8px';
                item.style.borderRadius = '8px';
                item.style.background = 'rgba(255,255,255,0.03)';
                item.style.fontSize = '12px';
                item.innerHTML = `
                    <span style="color:#a78bfa; font-weight:bold;">${msg.sender}:</span>
                    <span style="color:#e2e8f0; margin-left:4px;">${msg.text}</span>
                    <span style="float:right; font-size:9px; color:#64748b; margin-top:2px;">${msg.timestamp}</span>
                `;
                container.appendChild(item);
            });
            container.scrollTop = container.scrollHeight;
        } else {
            container.innerHTML = `<div style="color:#64748b; text-align:center; margin-top:20px; font-size:12px;">${currentLang === 'ru' ? 'Чат пуст. Призраки молчат...' : currentLang === 'en' ? 'Chat empty. Ghosts are silent...' : currentLang === 'kz' ? 'Чат бос. Елестер үнсіз...' : 'Chat bo\'sh. Arvoxlar sukut saqlashmoqda...'}</div>`;
        }
    } catch (e) {
        console.error("Ghost chat fetch error:", e);
    }
}

async function sendGhostChatMessage() {
    const input = document.getElementById('ghost-input');
    const text = input.value.trim();
    if (!text) return;
    
    try {
        const response = await fetch('/api/game/ghost-chat/send', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: userId,
                text: text
            })
        });
        const data = await response.json();
        if (data.success) {
            input.value = '';
            loadGhostChatMessages();
        } else {
            alert(data.error);
        }
    } catch (e) {
        console.error("Ghost message send error:", e);
    }
}

async function startTelegramStarsPayment(packageKey) {
    try {
        const response = await fetch('/api/payment/checkout', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: userId,
                package_key: packageKey
            })
        });
        const data = await response.json();
        if (data.success && data.invoice_link) {
            tg.openInvoice(data.invoice_link, function(status) {
                if (status === 'paid') {
                    alert("🎉");
                    loadProfile();
                }
            });
        } else {
            alert(data.error || "Invoice error");
        }
    } catch (e) {
        console.error(e);
        alert("Server bilan aloqada xatolik!");
    }
}

function startCardPayment(coins) {
    const url = `${window.location.origin}/payment/mock?user_id=${userId}&coins=${coins}`;
    tg.openLink(url);
}

// Add event listeners for profile activities
document.getElementById('select-lang').addEventListener('change', async (e) => {
    const selected = e.target.value;
    updateLang(selected);
    try {
        await fetch('/api/profile/language', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, language: selected })
        });
    } catch (err) {
        console.error("Language save failed:", err);
    }
});

document.getElementById('daily-claim-card').addEventListener('click', async () => {
    try {
        const response = await fetch('/api/daily-claim', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId })
        });
        const data = await response.json();
        if (data.success) {
            alert(`🎉 +${data.coins} Dark Coins!`);
            loadProfile();
        } else {
            alert(`⚠️ ${data.error}`);
        }
    } catch (err) {
        console.error(err);
    }
});

document.getElementById('btn-copy-ref').addEventListener('click', () => {
    const link = `https://t.me/darktownuz_bot?start=ref_${userId}`;
    navigator.clipboard.writeText(link).then(() => {
        alert(t("msg_copied"));
    }).catch(err => {
        const tempInput = document.createElement("input");
        tempInput.value = link;
        document.body.appendChild(tempInput);
        tempInput.select();
        document.execCommand("copy");
        document.body.removeChild(tempInput);
        alert(t("msg_copied"));
    });
});

document.getElementById('btn-send-ghost').addEventListener('click', sendGhostChatMessage);
document.getElementById('ghost-input').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendGhostChatMessage();
});

document.addEventListener('click', (e) => {
    if (e.target.classList.contains('btn-checkout')) {
        const pack = e.target.getAttribute('data-pack');
        startTelegramStarsPayment(pack);
    }
    if (e.target.classList.contains('btn-card-pay')) {
        const coins = e.target.getAttribute('data-coins');
        startCardPayment(coins);
    }
});

// Matchmaking & Party Event Listeners
document.getElementById('btn-create-party').addEventListener('click', createParty);
document.getElementById('btn-copy-party-link').addEventListener('click', copyPartyLink);
document.getElementById('btn-leave-party').addEventListener('click', leaveParty);
document.getElementById('btn-auto-match').addEventListener('click', autoMatchmaking);

document.getElementById('btn-toggle-create-opts').addEventListener('click', () => {
    const opts = document.getElementById('room-create-opts');
    opts.style.display = opts.style.display === 'none' ? 'block' : 'none';
});

document.getElementById('room-is-private').addEventListener('change', (e) => {
    const pinGroup = document.getElementById('room-pin-group');
    pinGroup.style.display = e.target.checked ? 'block' : 'none';
});

document.getElementById('btn-submit-create-room').addEventListener('click', submitCreateRoom);
document.getElementById('btn-submit-join-room').addEventListener('click', submitJoinRoom);
document.getElementById('btn-lobby-leave').addEventListener('click', leaveRoom);
document.getElementById('btn-lobby-start').addEventListener('click', startRoom);

document.getElementById('btn-send-room-day').addEventListener('click', sendRoomDayChatMessage);
document.getElementById('room-day-chat-input').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendRoomDayChatMessage();
});
