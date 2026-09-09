# 🏙 DarkTown Mafia Bot & WebApp — Complete Project Overview & Specification

This document provides a comprehensive technical, functional, and commercial breakdown of the **DarkTown Mafia Bot & Telegram Mini App** ecosystem for prospective buyers, investors, and developers.

---

## 📌 1. Executive Summary

**DarkTown** is an advanced, cyberpunk-themed **Mafia / Werewolf online gaming platform** built natively for Telegram. It combines a state-of-the-art **Telegram Mini App (WebApp)** with a robust **Group / Private Bot Engine**, offering both real-time web matchmaking and classic chat-based gameplay.

Players can jump into games with friends in private PIN-protected rooms, queue into public CS2-style matchmaking lobbies, complete quests, climb global leaderboards, and utilize strategic in-game shop boosters.

---

## 🚀 2. Technology Stack & Architecture

- **Backend Framework:** Python 3.11 - 3.13, iogram 3.x (High-performance async Telegram Bot framework), iohttp (Async Web Server & REST API).
- **Frontend (Mini App):** HTML5, Vanilla JavaScript (ES6+), Modern Neon Cyberpunk CSS3 UI, Telegram WebApp SDK.
- **Database Engine:** Async iosqlite (SQLite3) / PostgreSQL compatible.
- **Automated Cloud Backup:** Real-time and periodic encrypted database backup uploaded and pinned directly into a designated private Telegram Storage channel (Zero data loss guarantee).
- **Hosting & Deployment:** Render.com, VPS (Ubuntu/Debian), Railway, Docker, or Heroku with built-in **Self-Ping Keep-Alive** mechanism for 24/7 uninterrupted uptime.

---

## 🟢 3. Active Features Breakdown (Currently ON)

### 🎮 A. Real-Time Gameplay & Matchmaking
1. **CS2-Style Auto Matchmaking:** One-tap instant matchmaking connecting players to active open public lobbies.
2. **Private PIN-Protected Rooms:** Custom rooms with secret PIN codes for friends and communities.
3. **Custom Phase Timers:** Lobby hosts can configure custom Day discussion and Night action countdowns.
4. **Interactive Phase Transitions:** Immersive Day/Night/Voting/Execution cinematic transitions with sound effects.
5. **Three-Tier In-Game Chat System:**
   - ☀️ *Day Discussion Chat:* Public debate, voting, and suspect lynching.
   - 🔴 *Secret Mafia Chat:* Encrypted night coordination channel for the Mafia syndicate.
   - 👻 *Ghost Chat:* Dedicated spectator chat for eliminated players to watch the game unfold.

### 🎭 B. Dynamic Game Roles & Mechanics
- **🤵 Don (Mafia Boss):** Directs the mafia night attack and checks players to discover the Detective.
- **🔫 Mafia:** Collaborates to eliminate innocent citizens under the cover of darkness.
- **🕵️‍♂️ Detective (Commissar):** Inspects one player every night to reveal their true allegiance.
- **💉 Doctor:** Selects a player each night to heal and shield from assassination.
- **💋 Escort (Courtesan):** Blocks a player's night action through seductive distraction.
- **🤪 Maniac / Madman:** Lone-wolf survivor causing unpredictable chaos in the town.
- **👤 Innocent Citizens:** Use deductive reasoning and majority voting to purge crime.

### 🛒 C. Economy, Shop & Strategic Boosters
1. **🪙 Coin Economy:** Earned via victories, match participation, daily streaks, and referrals.
2. **🛡️ XP Shield:** Protects player XP and coins against night assassination (1-time consumption).
3. **⚡ Active Role Booster:** 100% guarantees receiving an active power role (Mafia, Detective, Doctor, etc.) rather than a standard civilian.
4. **🪪 Fake ID Card:** If you are Mafia and the Detective inspects you at night, you appear as an Innocent Citizen!
5. **⭐️ Native Monetization:** Telegram Stars and external payment gateway readiness for coin packages and VIP cosmetics.

### 🎁 D. Progression, Retention & Profiles
- **🔥 7-Day Daily Streak:** Escalating coin bonuses and rewards for daily active logins.
- **📋 Daily Quests:** Dynamic mission system offering extra rewards for in-game achievements.
- **👥 Referral Growth System:** Viral referral program granting **+50 Coins** per invited friend with antifraud verification.
- **🏆 Global Leaderboards:** Competitive ranking sorted by Wins, Total Matches, Winrate, and Level.
- **📊 Mafia Balance Calculator:** Interactive WebApp calculator displaying optimal role allocations for 4 to 15+ players.
- **👑 VIP Customization:** Custom Mini App animated backgrounds and VIP status badges.

### 🌍 E. Full 4-Language Localization
Instant client-side translation without page reloads across:
- 🇺🇿 **Uzbek (UZ)**
- 🇷🇺 **Russian (RU)**
- 🇬🇧 **English (EN)**
- 🇰🇿 **Kazakh (KZ)**

### 👑 F. Comprehensive Web & Bot Admin Panel
- **Live Analytics:** Total registered players, daily active users (DAU), matches played, economy circulation.
- **Player Management:** Search by Telegram ID, view stats, Ban / Unban players instantly.
- **Economy Control:** Add or deduct coins and XP from any user account.
- **📢 Global Broadcast System:** Broadcast rich media, text, and button announcements to all users simultaneously.
- **Maintenance Mode:** Instant toggle to lock the bot/app during major updates.

---

## 🟡 4. Plug-and-Play Modules Ready for Expansion (Currently OFF)

These modules are fully coded and structured in the codebase, but disabled in config.py for a lightweight MVP launch. They can be toggled ON at any moment with a single config flag:

1. **🛡️ Clan System (OFF):**
   - Create clans, recruit members, clan treasury, clan leaderboard, and clan wars.
2. **📜 Seasonal Battle Pass (OFF):**
   - 30-day tiered progression tracks, Free vs. Premium Battle Pass rewards, exclusive skins and badges.
3. **🏆 Tournament System (OFF):**
   - In-app tournament creator for admins, prize pool distribution, and automatic winner announcements.
4. **🎰 Casino & Mini-Games (OFF):**
   - Wheel of Fortune and coin roulette mini-games.

---

## 💼 5. Commercial Value & Monetization Streams

1. **Telegram Stars In-App Purchases:** High conversion monetization for cosmetic perks, boosters, and coin packs.
2. **Mandatory Channel Subscription (Sponsorships):** Force channel join before using the bot/app (Huge revenue from Telegram channel promotions).
3. **Advertising & Broadcasts:** Sell paid sponsored broadcasts to an engaged gaming audience.
4. **Organic Viral Growth:** Built-in referral mechanics encourage players to invite their social circles and group chats.

---

## 📦 6. Deliverables Included in Purchase

1. **Complete, Clean Source Code (100% Ownership):** Full Python backend + Vanilla JS/HTML5 frontend.
2. **Pre-configured Database & Automated Backup System.**
3. **5-Minute Deployment Guide** for Render, VPS, or Railway.
4. **Technical Onboarding & Setup Assistance.**

---
*DarkTown Mafia — A turnkey, high-engagement, profitable Web3/Telegram gaming asset.* 🚀
