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
            initCalculator();
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
async function loadActiveGame() {
    try {
        const response = await fetch(`/api/game/status?user_id=${userId}`);
        if (!response.ok) throw new Error("Game status fetch failed");
        
        const data = await response.json();
        const calcView = document.getElementById('match-calc-view');
        const gameView = document.getElementById('match-active-game-view');
        
        if (!data.inGame) {
            calcView.style.display = 'block';
            gameView.style.display = 'none';
            return;
        }
        
        // Inside active game!
        calcView.style.display = 'none';
        gameView.style.display = 'block';
        
        // Render phase
        const phaseBadge = document.getElementById('game-phase-badge');
        const phaseNames = {
            "lobby": "⏳ LOBBI",
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
                        // Mafia kill
                        if (p.role !== "Mafia" && p.role !== "Don") {
                            addActionBtn(actionsContainer, "🔴 O'ldirish", () => sendAction(p.user_id, "mafia"), "shoot");
                        }
                    }
                    if (data.myRole === "Don") {
                        // Don check
                        addActionBtn(actionsContainer, "🔍 Tekshirish", () => sendAction(p.user_id, "don"), "check");
                    }
                    if (data.myRole === "Detective") {
                        // Detective choice: check or shoot
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
        
    } catch (e) {
        console.error("Active game fetch error:", e);
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
