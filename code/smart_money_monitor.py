"""
Smart Money Tracker - Real-time wallet performance monitoring
Tracks pump.fun trades and identifies high-performing wallets
"""

import asyncio
import websockets
import json
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SmartMoneyTracker:
    def __init__(self, db_path: str = "data/smart_money_tracker.db"):
        self.db_path = db_path
        self.ws_url = "wss://pumpportal.fun/api/data"
        self.init_database()
        
    def init_database(self):
        """Initialize database with schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Read and execute schema
        with open('data/smart_money_tracker_schema.sql', 'r') as f:
            schema = f.read()
            cursor.executescript(schema)
        
        conn.commit()
        conn.close()
        logger.info(f"Database initialized at {self.db_path}")
    
    def process_trade(self, event: Dict) -> bool:
        """Process a trade event and update wallet performance"""
        try:
            # Extract trade data
            tx_type = event.get('txType')
            if tx_type not in ['buy', 'sell']:
                return False
            
            wallet = event.get('traderPublicKey')
            token_addr = event.get('mint')
            token_name = event.get('name', 'Unknown')
            token_symbol = event.get('symbol', 'UNKNOWN')
            sol_amount = float(event.get('solAmount', 0))
            token_amount = float(event.get('tokenAmount', 0))
            signature = event.get('signature')
            timestamp = int(event.get('timestamp', time.time() * 1000)) // 1000
            
            # Get token price (SOL per token)
            price = sol_amount / token_amount if token_amount > 0 else 0
            
            if not wallet or not token_addr or sol_amount <= 0:
                return False
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Ensure wallet exists
            self._ensure_wallet_exists(cursor, wallet, timestamp)
            
            # Insert trade
            cursor.execute("""
                INSERT OR IGNORE INTO trades 
                (wallet_address, token_address, token_name, token_symbol, action, 
                 amount_sol, amount_tokens, timestamp, price_at_trade, signature)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (wallet, token_addr, token_name, token_symbol, tx_type, 
                  sol_amount, token_amount, timestamp, price, signature))
            
            trade_id = cursor.lastrowid
            
            # Handle position tracking
            if tx_type == 'buy':
                self._open_position(cursor, wallet, token_addr, token_name, token_symbol,
                                  trade_id, timestamp, price, sol_amount, token_amount)
            elif tx_type == 'sell':
                self._close_position(cursor, wallet, token_addr, trade_id, 
                                   timestamp, price, sol_amount, token_amount)
            
            # Update wallet stats
            self._update_wallet_stats(cursor, wallet)
            
            # Calculate performance score
            self._calculate_performance_score(cursor, wallet)
            
            # Check if we should trigger alerts
            if tx_type == 'buy':
                self._check_alerts(cursor, wallet, trade_id, sol_amount)
            
            conn.commit()
            conn.close()
            
            logger.info(f"{tx_type.upper()} | {wallet[:8]}... | {token_symbol} | {sol_amount:.2f} SOL")
            return True
            
        except Exception as e:
            logger.error(f"Error processing trade: {e}")
            return False
    
    def _ensure_wallet_exists(self, cursor, wallet: str, timestamp: int):
        """Create wallet record if it doesn't exist"""
        cursor.execute("""
            INSERT OR IGNORE INTO wallets (address, first_seen, last_active)
            VALUES (?, ?, ?)
        """, (wallet, timestamp, timestamp))
        
        # Update last_active
        cursor.execute("""
            UPDATE wallets SET last_active = ? WHERE address = ?
        """, (timestamp, wallet))
    
    def _open_position(self, cursor, wallet: str, token: str, name: str, symbol: str,
                       trade_id: int, timestamp: int, price: float, sol: float, tokens: float):
        """Open a new position when wallet buys"""
        cursor.execute("""
            INSERT INTO positions 
            (wallet_address, token_address, token_name, token_symbol, entry_trade_id,
             entry_timestamp, entry_price, entry_amount_sol, entry_amount_tokens, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'open')
        """, (wallet, token, name, symbol, trade_id, timestamp, price, sol, tokens))
    
    def _close_position(self, cursor, wallet: str, token: str, trade_id: int,
                        timestamp: int, price: float, sol: float, tokens: float):
        """Close existing position when wallet sells"""
        # Find oldest open position for this wallet+token
        cursor.execute("""
            SELECT id, entry_timestamp, entry_price, entry_amount_sol, entry_amount_tokens
            FROM positions
            WHERE wallet_address = ? AND token_address = ? AND status = 'open'
            ORDER BY entry_timestamp ASC
            LIMIT 1
        """, (wallet, token))
        
        position = cursor.fetchone()
        if not position:
            logger.warning(f"No open position found for {wallet[:8]}... selling {token[:8]}...")
            return
        
        pos_id, entry_ts, entry_price, entry_sol, entry_tokens = position
        
        # Calculate profit
        profit_sol = sol - entry_sol
        profit_percent = (profit_sol / entry_sol * 100) if entry_sol > 0 else 0
        hold_time_mins = (timestamp - entry_ts) // 60
        
        # Update position
        cursor.execute("""
            UPDATE positions
            SET exit_trade_id = ?, exit_timestamp = ?, exit_price = ?,
                exit_amount_sol = ?, profit_sol = ?, profit_percent = ?,
                hold_time_mins = ?, status = 'closed'
            WHERE id = ?
        """, (trade_id, timestamp, price, sol, profit_sol, profit_percent, hold_time_mins, pos_id))
    
    def _update_wallet_stats(self, cursor, wallet: str):
        """Update wallet statistics based on closed positions"""
        # Count wins/losses
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN profit_sol > 0 THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN profit_sol <= 0 THEN 1 ELSE 0 END) as losses,
                SUM(profit_sol) as total_profit,
                AVG(hold_time_mins) as avg_hold
            FROM positions
            WHERE wallet_address = ? AND status = 'closed'
        """, (wallet,))
        
        stats = cursor.fetchone()
        if not stats or stats[0] == 0:
            return
        
        total, wins, losses, total_profit, avg_hold = stats
        
        # Calculate 24h and 7d metrics
        now = int(time.time())
        day_ago = now - 86400
        week_ago = now - 604800
        
        # Volume metrics
        cursor.execute("""
            SELECT SUM(amount_sol) 
            FROM trades 
            WHERE wallet_address = ? AND action = 'buy' AND timestamp >= ?
        """, (wallet, day_ago))
        vol_24h = cursor.fetchone()[0] or 0
        
        cursor.execute("""
            SELECT SUM(amount_sol)
            FROM trades
            WHERE wallet_address = ? AND action = 'buy' AND timestamp >= ?
        """, (wallet, week_ago))
        vol_7d = cursor.fetchone()[0] or 0
        
        # ROI metrics (profit from positions closed in period)
        cursor.execute("""
            SELECT SUM(profit_sol), SUM(entry_amount_sol)
            FROM positions
            WHERE wallet_address = ? AND status = 'closed' 
                AND exit_timestamp >= ?
        """, (wallet, day_ago))
        roi_24h_data = cursor.fetchone()
        roi_24h = (roi_24h_data[0] / roi_24h_data[1] * 100) if roi_24h_data[1] else 0
        
        cursor.execute("""
            SELECT SUM(profit_sol), SUM(entry_amount_sol)
            FROM positions
            WHERE wallet_address = ? AND status = 'closed'
                AND exit_timestamp >= ?
        """, (wallet, week_ago))
        roi_7d_data = cursor.fetchone()
        roi_7d = (roi_7d_data[0] / roi_7d_data[1] * 100) if roi_7d_data[1] else 0
        
        # Update wallet record
        cursor.execute("""
            UPDATE wallets
            SET total_trades = ?,
                wins = ?,
                losses = ?,
                total_profit_sol = ?,
                avg_hold_time_mins = ?,
                volume_24h = ?,
                volume_7d = ?,
                roi_24h = ?,
                roi_7d = ?
            WHERE address = ?
        """, (total, wins, losses, total_profit, avg_hold, vol_24h, vol_7d, 
              roi_24h, roi_7d, wallet))
    
    def _calculate_performance_score(self, cursor, wallet: str):
        """Calculate 0-100 performance score for wallet"""
        cursor.execute("""
            SELECT total_trades, wins, losses, roi_7d, volume_7d, last_active
            FROM wallets
            WHERE address = ?
        """, (wallet,))
        
        data = cursor.fetchone()
        if not data or data[0] < 3:  # Need at least 3 trades
            score = 0
        else:
            total, wins, losses, roi_7d, vol_7d, last_active = data
            
            # Win rate component (40%)
            win_rate = (wins / total * 100) if total > 0 else 0
            win_score = win_rate * 0.4
            
            # ROI component (30%) - normalize to 0-100
            roi_score = min(max(roi_7d / 10, 0), 100) * 0.3
            
            # Volume component (15%) - normalize (50 SOL = 100 points)
            vol_score = min(vol_7d / 50 * 100, 100) * 0.15
            
            # Recency bonus (15%)
            now = int(time.time())
            if last_active >= now - 86400:  # Active in last 24h
                recency_score = 100 * 0.15
            elif last_active >= now - 604800:  # Active in last 7d
                recency_score = 50 * 0.15
            else:
                recency_score = 0
            
            score = win_score + roi_score + vol_score + recency_score
        
        cursor.execute("""
            UPDATE wallets SET performance_score = ? WHERE address = ?
        """, (score, wallet))
    
    def _check_alerts(self, cursor, wallet: str, trade_id: int, sol_amount: float):
        """Check if this trade should trigger any alerts"""
        cursor.execute("""
            SELECT ac.id, ac.alert_type, ac.alert_destination, w.performance_score
            FROM alert_configs ac
            JOIN wallets w ON ac.wallet_address = w.address
            WHERE ac.wallet_address = ? 
                AND ac.is_active = 1
                AND w.performance_score >= ac.min_performance_score
                AND ? >= ac.min_buy_amount_sol
        """, (wallet, sol_amount))
        
        alerts = cursor.fetchall()
        for alert_id, alert_type, destination, score in alerts:
            # Queue alert (will be processed by separate alert service)
            cursor.execute("""
                INSERT INTO alert_history (alert_config_id, wallet_address, trade_id, sent_at, status)
                VALUES (?, ?, ?, ?, 'queued')
            """, (alert_id, wallet, trade_id, int(time.time())))
            
            logger.info(f"🚨 ALERT QUEUED: {wallet[:8]}... (score: {score:.1f}) -> {alert_type}")
    
    async def monitor(self):
        """Main monitoring loop - connect to WebSocket and process trades"""
        subscription_payload = {
            "method": "subscribeNewToken"
        }
        
        while True:
            try:
                async with websockets.connect(self.ws_url) as websocket:
                    await websocket.send(json.dumps(subscription_payload))
                    logger.info("Connected to pump.fun WebSocket, monitoring trades...")
                    
                    async for message in websocket:
                        try:
                            event = json.loads(message)
                            self.process_trade(event)
                        except json.JSONDecodeError:
                            continue
                        except Exception as e:
                            logger.error(f"Error processing message: {e}")
                            
            except websockets.exceptions.ConnectionClosed:
                logger.warning("WebSocket connection closed, reconnecting in 5s...")
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"WebSocket error: {e}, reconnecting in 10s...")
                await asyncio.sleep(10)

    def get_leaderboard(self, limit: int = 20) -> List[Dict]:
        """Get top performing wallets"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT address, performance_score, total_trades, wins, losses, 
                   total_profit_sol, roi_7d, volume_7d, last_active
            FROM wallets
            WHERE total_trades >= 5
            ORDER BY performance_score DESC
            LIMIT ?
        """, (limit,))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'address': row[0],
                'score': round(row[1], 1),
                'total_trades': row[2],
                'wins': row[3],
                'losses': row[4],
                'win_rate': round(row[3] / row[2] * 100, 1) if row[2] > 0 else 0,
                'total_profit_sol': round(row[5], 2),
                'roi_7d': round(row[6], 1),
                'volume_7d': round(row[7], 2),
                'last_active': row[8]
            })
        
        conn.close()
        return results

if __name__ == "__main__":
    tracker = SmartMoneyTracker()
    asyncio.run(tracker.monitor())
