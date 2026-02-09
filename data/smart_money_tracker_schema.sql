-- Smart Money Tracker Database Schema

-- Wallets table - tracks all wallet performance metrics
CREATE TABLE IF NOT EXISTS wallets (
    address TEXT PRIMARY KEY,
    first_seen INTEGER NOT NULL,
    last_active INTEGER NOT NULL,
    total_trades INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    total_profit_sol REAL DEFAULT 0,
    avg_hold_time_mins INTEGER DEFAULT 0,
    performance_score REAL DEFAULT 0,
    is_tracked BOOLEAN DEFAULT 0,
    volume_24h REAL DEFAULT 0,
    volume_7d REAL DEFAULT 0,
    roi_24h REAL DEFAULT 0,
    roi_7d REAL DEFAULT 0
);

-- Trades table - individual buy/sell transactions
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    wallet_address TEXT NOT NULL,
    token_address TEXT NOT NULL,
    token_name TEXT,
    token_symbol TEXT,
    action TEXT NOT NULL CHECK(action IN ('buy', 'sell')),
    amount_sol REAL NOT NULL,
    amount_tokens REAL,
    timestamp INTEGER NOT NULL,
    price_at_trade REAL,
    signature TEXT UNIQUE,
    FOREIGN KEY (wallet_address) REFERENCES wallets(address)
);

-- Positions table - track open positions for PnL calculation
CREATE TABLE IF NOT EXISTS positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    wallet_address TEXT NOT NULL,
    token_address TEXT NOT NULL,
    token_name TEXT,
    token_symbol TEXT,
    entry_trade_id INTEGER NOT NULL,
    entry_timestamp INTEGER NOT NULL,
    entry_price REAL NOT NULL,
    entry_amount_sol REAL NOT NULL,
    entry_amount_tokens REAL NOT NULL,
    exit_trade_id INTEGER,
    exit_timestamp INTEGER,
    exit_price REAL,
    exit_amount_sol REAL,
    profit_sol REAL,
    profit_percent REAL,
    hold_time_mins INTEGER,
    status TEXT DEFAULT 'open' CHECK(status IN ('open', 'closed')),
    FOREIGN KEY (wallet_address) REFERENCES wallets(address),
    FOREIGN KEY (entry_trade_id) REFERENCES trades(id),
    FOREIGN KEY (exit_trade_id) REFERENCES trades(id)
);

-- Performance snapshots for historical tracking
CREATE TABLE IF NOT EXISTS performance_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    wallet_address TEXT NOT NULL,
    snapshot_time INTEGER NOT NULL,
    win_rate REAL,
    roi_7d REAL,
    roi_24h REAL,
    volume_7d REAL,
    volume_24h REAL,
    performance_score REAL,
    total_trades INTEGER,
    FOREIGN KEY (wallet_address) REFERENCES wallets(address)
);

-- Alert configurations
CREATE TABLE IF NOT EXISTS alert_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    wallet_address TEXT NOT NULL,
    alert_type TEXT NOT NULL CHECK(alert_type IN ('telegram', 'webhook', 'email')),
    alert_destination TEXT NOT NULL,
    min_performance_score REAL DEFAULT 70,
    min_buy_amount_sol REAL DEFAULT 0.1,
    is_active BOOLEAN DEFAULT 1,
    created_at INTEGER NOT NULL,
    FOREIGN KEY (wallet_address) REFERENCES wallets(address)
);

-- Alert history
CREATE TABLE IF NOT EXISTS alert_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_config_id INTEGER NOT NULL,
    wallet_address TEXT NOT NULL,
    trade_id INTEGER NOT NULL,
    sent_at INTEGER NOT NULL,
    status TEXT DEFAULT 'sent' CHECK(status IN ('sent', 'failed', 'queued')),
    FOREIGN KEY (alert_config_id) REFERENCES alert_configs(id),
    FOREIGN KEY (trade_id) REFERENCES trades(id)
);

-- Tokens table - cache token metadata
CREATE TABLE IF NOT EXISTS tokens (
    address TEXT PRIMARY KEY,
    name TEXT,
    symbol TEXT,
    created_at INTEGER,
    total_volume_sol REAL DEFAULT 0,
    unique_traders INTEGER DEFAULT 0,
    last_updated INTEGER
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_wallets_score ON wallets(performance_score DESC);
CREATE INDEX IF NOT EXISTS idx_wallets_tracked ON wallets(is_tracked);
CREATE INDEX IF NOT EXISTS idx_wallets_last_active ON wallets(last_active DESC);
CREATE INDEX IF NOT EXISTS idx_trades_wallet ON trades(wallet_address);
CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_trades_token ON trades(token_address);
CREATE INDEX IF NOT EXISTS idx_trades_signature ON trades(signature);
CREATE INDEX IF NOT EXISTS idx_positions_wallet ON positions(wallet_address);
CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status);
CREATE INDEX IF NOT EXISTS idx_positions_token ON positions(token_address);
CREATE INDEX IF NOT EXISTS idx_alerts_user ON alert_configs(user_id);
CREATE INDEX IF NOT EXISTS idx_alerts_wallet ON alert_configs(wallet_address);
CREATE INDEX IF NOT EXISTS idx_alert_history_sent ON alert_history(sent_at DESC);
