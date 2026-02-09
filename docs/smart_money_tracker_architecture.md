# Smart Money Tracker - System Architecture

## Overview
Track high-performing wallets on pump.fun and alert users when they buy tokens, enabling copy-trading opportunities.

## Core Components

### 1. Wallet Performance Tracker
**Purpose:** Continuously monitor and score wallets based on trading performance

**Data Model:**
```sql
-- Wallets table
CREATE TABLE wallets (
    address TEXT PRIMARY KEY,
    first_seen INTEGER,
    last_active INTEGER,
    total_trades INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    total_profit_sol REAL DEFAULT 0,
    avg_hold_time_mins INTEGER,
    performance_score REAL DEFAULT 0,
    is_tracked BOOLEAN DEFAULT 0
);

-- Trades table
CREATE TABLE trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    wallet_address TEXT,
    token_address TEXT,
    token_name TEXT,
    token_symbol TEXT,
    action TEXT, -- 'buy' or 'sell'
    amount_sol REAL,
    amount_tokens REAL,
    timestamp INTEGER,
    price_at_trade REAL,
    FOREIGN KEY (wallet_address) REFERENCES wallets(address)
);

-- Wallet performance snapshots (for historical tracking)
CREATE TABLE performance_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    wallet_address TEXT,
    snapshot_time INTEGER,
    win_rate REAL,
    roi_7d REAL,
    roi_24h REAL,
    volume_7d REAL,
    performance_score REAL,
    FOREIGN KEY (wallet_address) REFERENCES wallets(address)
);

-- User alert configurations
CREATE TABLE alert_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    wallet_address TEXT,
    alert_type TEXT, -- 'telegram', 'webhook'
    alert_destination TEXT, -- telegram chat_id or webhook URL
    min_performance_score REAL DEFAULT 70,
    is_active BOOLEAN DEFAULT 1,
    created_at INTEGER
);
```

**Scoring Algorithm:**
```
performance_score = (
    win_rate * 40 +                    # 40% weight on success rate
    normalized_roi_7d * 30 +           # 30% weight on 7-day ROI
    normalized_volume_7d * 15 +        # 15% weight on activity level
    recency_bonus * 15                 # 15% weight on recent activity
)

Where:
- win_rate = wins / total_trades * 100
- normalized_roi_7d = min(roi_7d / 10, 100)  # Cap at 1000% = 100 points
- normalized_volume_7d = min(volume_sol / 50, 100)  # Cap at 50 SOL = 100 points
- recency_bonus = 100 if active in last 24h, 50 if last 7d, 0 otherwise
```

### 2. Real-Time WebSocket Monitor
**Purpose:** Listen to pump.fun trades and update wallet performance in real-time

**Flow:**
1. Connect to pump.fun WebSocket
2. On new trade event:
   - Extract wallet address, token, amount, action (buy/sell)
   - Insert trade record
   - Update wallet statistics (total_trades, wins/losses, profit)
   - Recalculate performance_score
   - If wallet is tracked AND meets alert thresholds → trigger alert

**Key Functions:**
- `process_trade_event(event)` - Parse and store trade
- `update_wallet_performance(wallet_address)` - Recalculate stats
- `check_alert_triggers(wallet_address, trade)` - Send alerts if conditions met

### 3. Telegram Alert Bot
**Purpose:** Send instant notifications when tracked wallets buy

**Alert Format:**
```
🚀 SMART MONEY BUY ALERT

Wallet: ABC...XYZ (Score: 87/100)
Token: $SYMBOL (TokenName)
Amount: 5.2 SOL (~$850)

📊 Wallet Stats:
- Win Rate: 73% (22W/8L)
- 7D ROI: +342%
- Avg Hold: 4.2 hours

🔗 Buy on pump.fun: [link]
👁️ Track wallet: [link]
```

**Setup:**
- Python `python-telegram-bot` library
- Bot token stored as environment variable
- Users subscribe via `/track <wallet_address>` command
- Bot commands:
  - `/track <address>` - Start tracking wallet
  - `/untrack <address>` - Stop tracking
  - `/list` - Show your tracked wallets
  - `/leaderboard` - Top 10 performing wallets
  - `/score <address>` - Check wallet score

### 4. Wallet Discovery Engine
**Purpose:** Automatically identify high-performing wallets to suggest for tracking

**Strategy:**
- Monitor all pump.fun trades for 7 days
- Calculate performance scores for all active wallets
- Surface top 20 wallets daily
- Users can browse and add to tracking list

### 5. Web Dashboard (MVP)
**Purpose:** Simple interface to view leaderboard and configure alerts

**Pages:**
- `/leaderboard` - Top performing wallets (public)
- `/dashboard` - User's tracked wallets and recent alerts
- `/wallet/<address>` - Detailed wallet stats and trade history
- `/settings` - Configure Telegram bot, alert thresholds

**Tech Stack:**
- FastAPI backend (reuse existing Python code)
- Simple HTML/CSS frontend (no React needed for MVP)
- SQLite database (same as backend)

## Deployment Architecture

### Phase 1: MVP (Single Server)
```
┌─────────────────────────────────────┐
│   VPS (4GB RAM, 2 CPU)              │
│                                     │
│  ┌──────────────────────────────┐  │
│  │  WebSocket Monitor Process   │  │
│  │  (background daemon)         │  │
│  └──────────────────────────────┘  │
│                                     │
│  ┌──────────────────────────────┐  │
│  │  Telegram Bot Process        │  │
│  │  (background daemon)         │  │
│  └──────────────────────────────┘  │
│                                     │
│  ┌──────────────────────────────┐  │
│  │  FastAPI Web Server          │  │
│  │  (serves dashboard + API)    │  │
│  └──────────────────────────────┘  │
│                                     │
│  ┌──────────────────────────────┐  │
│  │  SQLite Database             │  │
│  │  coordination_detection.db   │  │
│  └──────────────────────────────┘  │
└─────────────────────────────────────┘
```

### Phase 2: Scale (If Needed)
- Move to PostgreSQL for concurrent writes
- Separate alert service to dedicated server
- Add Redis for caching wallet scores
- CDN for dashboard static assets

## Monetization Tiers

### Free Tier
- Track up to 3 wallets
- 5 alerts per day
- 24-hour delayed leaderboard access
- No auto-copy trading

### Pro Tier ($49/month)
- Track unlimited wallets
- Real-time alerts (Telegram + webhook)
- Full leaderboard access
- Historical wallet analysis
- Export trade data

### Premium Tier ($99/month)
- Everything in Pro
- Auto-copy trading (via API integration)
- Priority alert delivery (<1s latency)
- Custom alert logic/filters
- API access for building custom tools

## MVP Build Order

1. **Database schema** - Set up new tables for wallet tracking
2. **Refactor WebSocket monitor** - Track profitability instead of coordination
3. **Scoring system** - Implement performance score calculation
4. **Telegram bot** - Basic alert delivery
5. **Web dashboard** - Simple leaderboard + wallet detail pages
6. **Testing** - Run for 24 hours with real data, validate alerts

## Success Metrics

**Week 1:**
- 10+ high-performing wallets identified
- Alert system working with <5s latency
- 5+ beta users tracking wallets

**Month 1:**
- 50+ active users
- 10+ paying Pro users ($490 MRR)
- 90%+ alert accuracy (no spam)

**Month 3:**
- 200+ active users
- 50+ paying users ($2,450 MRR)
- Feature requests guiding Premium tier development
