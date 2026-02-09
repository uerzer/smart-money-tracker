"""
Smart Money Tracker - Telegram Alert Bot
Sends real-time alerts when tracked wallets buy tokens
"""

import asyncio
import sqlite3
import time
import os
from typing import Dict, List, Optional
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TelegramAlertBot:
    def __init__(self, token: str, db_path: str = "data/smart_money_tracker.db"):
        self.token = token
        self.db_path = db_path
        self.app = None
        
    def init_bot(self):
        """Initialize the Telegram bot application"""
        self.app = Application.builder().token(self.token).build()
        
        # Register command handlers
        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("track", self.cmd_track))
        self.app.add_handler(CommandHandler("untrack", self.cmd_untrack))
        self.app.add_handler(CommandHandler("list", self.cmd_list))
        self.app.add_handler(CommandHandler("leaderboard", self.cmd_leaderboard))
        self.app.add_handler(CommandHandler("score", self.cmd_score))
        self.app.add_handler(CommandHandler("help", self.cmd_help))
        
        # Callback query handler for inline buttons
        self.app.add_handler(CallbackQueryHandler(self.button_callback))
        
        logger.info("Telegram bot initialized")
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        welcome_msg = """
🚀 **Welcome to Smart Money Tracker!**

Track high-performing wallets on pump.fun and get instant alerts when they buy.

**Commands:**
/track <wallet> - Start tracking a wallet
/untrack <wallet> - Stop tracking a wallet
/list - Show your tracked wallets
/leaderboard - Top 10 performing wallets
/score <wallet> - Check wallet performance score
/help - Show this help message

**Example:**
`/track 7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU`

Ready to find smart money? Check the /leaderboard!
"""
        await update.message.reply_text(welcome_msg, parse_mode='Markdown')
    
    async def cmd_track(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /track <wallet> command"""
        if not context.args:
            await update.message.reply_text(
                "❌ Usage: `/track <wallet_address>`\n"
                "Example: `/track 7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU`",
                parse_mode='Markdown'
            )
            return
        
        wallet = context.args[0].strip()
        user_id = str(update.effective_user.id)
        chat_id = str(update.effective_chat.id)
        
        # Validate wallet exists and has data
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT address, performance_score, total_trades, wins, losses
            FROM wallets WHERE address = ?
        """, (wallet,))
        
        wallet_data = cursor.fetchone()
        
        if not wallet_data:
            await update.message.reply_text(
                f"❌ Wallet not found in our database.\n"
                f"This wallet hasn't made any trades yet, or we haven't tracked it.\n\n"
                f"Check the /leaderboard for high-performing wallets to track!"
            )
            conn.close()
            return
        
        addr, score, total, wins, losses = wallet_data
        
        # Check if already tracking
        cursor.execute("""
            SELECT id FROM alert_configs
            WHERE user_id = ? AND wallet_address = ? AND is_active = 1
        """, (user_id, wallet))
        
        if cursor.fetchone():
            await update.message.reply_text(f"✅ You're already tracking this wallet!")
            conn.close()
            return
        
        # Add alert config
        cursor.execute("""
            INSERT INTO alert_configs 
            (user_id, wallet_address, alert_type, alert_destination, created_at)
            VALUES (?, ?, 'telegram', ?, ?)
        """, (user_id, wallet, chat_id, int(time.time())))
        
        # Mark wallet as tracked
        cursor.execute("""
            UPDATE wallets SET is_tracked = 1 WHERE address = ?
        """, (wallet,))
        
        conn.commit()
        conn.close()
        
        win_rate = (wins / total * 100) if total > 0 else 0
        
        msg = f"""
✅ **Now tracking wallet!**

📊 **Wallet Stats:**
Score: {score:.1f}/100
Win Rate: {win_rate:.1f}% ({wins}W/{losses}L)
Total Trades: {total}

You'll receive alerts when this wallet buys tokens on pump.fun.

Wallet: `{wallet[:8]}...{wallet[-8:]}`
"""
        await update.message.reply_text(msg, parse_mode='Markdown')
    
    async def cmd_untrack(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /untrack <wallet> command"""
        if not context.args:
            await update.message.reply_text(
                "❌ Usage: `/untrack <wallet_address>`\n"
                "Or use /list to see your tracked wallets.",
                parse_mode='Markdown'
            )
            return
        
        wallet = context.args[0].strip()
        user_id = str(update.effective_user.id)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Deactivate alert config
        cursor.execute("""
            UPDATE alert_configs 
            SET is_active = 0
            WHERE user_id = ? AND wallet_address = ?
        """, (user_id, wallet))
        
        if cursor.rowcount == 0:
            await update.message.reply_text("❌ You're not tracking this wallet.")
            conn.close()
            return
        
        conn.commit()
        conn.close()
        
        await update.message.reply_text(
            f"✅ Stopped tracking wallet `{wallet[:8]}...{wallet[-8:]}`",
            parse_mode='Markdown'
        )
    
    async def cmd_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /list command - show tracked wallets"""
        user_id = str(update.effective_user.id)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT w.address, w.performance_score, w.total_trades, w.wins, w.losses
            FROM alert_configs ac
            JOIN wallets w ON ac.wallet_address = w.address
            WHERE ac.user_id = ? AND ac.is_active = 1
            ORDER BY w.performance_score DESC
        """, (user_id,))
        
        tracked = cursor.fetchall()
        conn.close()
        
        if not tracked:
            await update.message.reply_text(
                "📭 You're not tracking any wallets yet.\n\n"
                "Use /leaderboard to find high-performing wallets to track!"
            )
            return
        
        msg = "📋 **Your Tracked Wallets:**\n\n"
        for addr, score, total, wins, losses in tracked:
            win_rate = (wins / total * 100) if total > 0 else 0
            msg += f"• `{addr[:8]}...{addr[-8:]}`\n"
            msg += f"  Score: {score:.1f}/100 | WR: {win_rate:.1f}% | Trades: {total}\n\n"
        
        await update.message.reply_text(msg, parse_mode='Markdown')
    
    async def cmd_leaderboard(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /leaderboard command - show top wallets"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT address, performance_score, total_trades, wins, losses, roi_7d, volume_7d
            FROM wallets
            WHERE total_trades >= 5
            ORDER BY performance_score DESC
            LIMIT 10
        """, ())
        
        leaderboard = cursor.fetchall()
        conn.close()
        
        if not leaderboard:
            await update.message.reply_text(
                "📊 Leaderboard is empty. Start monitoring to collect data!"
            )
            return
        
        msg = "🏆 **Top 10 Smart Money Wallets**\n\n"
        for i, (addr, score, total, wins, losses, roi_7d, vol_7d) in enumerate(leaderboard, 1):
            win_rate = (wins / total * 100) if total > 0 else 0
            msg += f"{i}. Score: {score:.1f}/100\n"
            msg += f"   `{addr[:8]}...{addr[-8:]}`\n"
            msg += f"   WR: {win_rate:.1f}% | ROI 7d: {roi_7d:+.1f}% | Vol: {vol_7d:.1f} SOL\n\n"
        
        msg += "Use `/track <wallet>` to get alerts when they buy!"
        
        await update.message.reply_text(msg, parse_mode='Markdown')
    
    async def cmd_score(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /score <wallet> command - show detailed wallet stats"""
        if not context.args:
            await update.message.reply_text(
                "❌ Usage: `/score <wallet_address>`",
                parse_mode='Markdown'
            )
            return
        
        wallet = context.args[0].strip()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT performance_score, total_trades, wins, losses, total_profit_sol,
                   avg_hold_time_mins, roi_7d, roi_24h, volume_7d, volume_24h, last_active
            FROM wallets
            WHERE address = ?
        """, (wallet,))
        
        data = cursor.fetchone()
        
        if not data:
            await update.message.reply_text("❌ Wallet not found in our database.")
            conn.close()
            return
        
        score, total, wins, losses, profit, avg_hold, roi_7d, roi_24h, vol_7d, vol_24h, last_active = data
        
        win_rate = (wins / total * 100) if total > 0 else 0
        
        # Get recent trades
        cursor.execute("""
            SELECT token_symbol, action, amount_sol, timestamp
            FROM trades
            WHERE wallet_address = ?
            ORDER BY timestamp DESC
            LIMIT 5
        """, (wallet,))
        
        recent = cursor.fetchall()
        conn.close()
        
        # Format last active time
        time_diff = int(time.time()) - last_active
        if time_diff < 3600:
            last_active_str = f"{time_diff // 60}m ago"
        elif time_diff < 86400:
            last_active_str = f"{time_diff // 3600}h ago"
        else:
            last_active_str = f"{time_diff // 86400}d ago"
        
        msg = f"""
📊 **Wallet Performance Report**

🎯 **Score:** {score:.1f}/100

📈 **Stats:**
Win Rate: {win_rate:.1f}% ({wins}W/{losses}L)
Total Trades: {total}
Total Profit: {profit:.2f} SOL

⏱️ **Activity:**
Avg Hold Time: {avg_hold // 60}h {avg_hold % 60}m
Last Active: {last_active_str}

💰 **ROI:**
24h: {roi_24h:+.1f}%
7d: {roi_7d:+.1f}%

📊 **Volume:**
24h: {vol_24h:.2f} SOL
7d: {vol_7d:.2f} SOL

🔥 **Recent Trades:**
"""
        
        for symbol, action, sol, ts in recent:
            emoji = "🟢" if action == "buy" else "🔴"
            msg += f"{emoji} {action.upper()} ${symbol} - {sol:.2f} SOL\n"
        
        msg += f"\nWallet: `{wallet[:8]}...{wallet[-8:]}`"
        
        await update.message.reply_text(msg, parse_mode='Markdown')
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        await self.cmd_start(update, context)
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button clicks from inline keyboards"""
        query = update.callback_query
        await query.answer()
        
        # Future: handle inline button actions (track/untrack from leaderboard)
    
    async def send_buy_alert(self, chat_id: str, wallet: str, trade_data: Dict):
        """Send buy alert to user"""
        try:
            token_symbol = trade_data.get('token_symbol', 'UNKNOWN')
            token_name = trade_data.get('token_name', 'Unknown Token')
            token_addr = trade_data.get('token_address', '')
            sol_amount = trade_data.get('amount_sol', 0)
            score = trade_data.get('wallet_score', 0)
            win_rate = trade_data.get('win_rate', 0)
            total_trades = trade_data.get('total_trades', 0)
            wins = trade_data.get('wins', 0)
            losses = trade_data.get('losses', 0)
            
            # Calculate USD estimate (assuming $200/SOL)
            usd_amount = sol_amount * 200
            
            msg = f"""
🚀 **SMART MONEY BUY ALERT**

💎 **Token:** ${token_symbol}
{token_name}

💰 **Amount:** {sol_amount:.2f} SOL (~${usd_amount:.0f})

📊 **Wallet Stats:**
Score: {score:.1f}/100
Win Rate: {win_rate:.1f}% ({wins}W/{losses}L)
Total Trades: {total_trades}

🔗 [Buy on pump.fun](https://pump.fun/{token_addr})
👁️ Wallet: `{wallet[:8]}...{wallet[-8:]}`
"""
            
            await self.app.bot.send_message(
                chat_id=chat_id,
                text=msg,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
            
            logger.info(f"Alert sent to {chat_id}: {wallet[:8]}... bought ${token_symbol}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send alert: {e}")
            return False
    
    async def process_alert_queue(self):
        """Background task to process queued alerts"""
        while True:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Get queued alerts
                cursor.execute("""
                    SELECT ah.id, ah.alert_config_id, ah.wallet_address, ah.trade_id,
                           ac.alert_destination,
                           t.token_address, t.token_name, t.token_symbol, t.amount_sol,
                           w.performance_score, w.total_trades, w.wins, w.losses
                    FROM alert_history ah
                    JOIN alert_configs ac ON ah.alert_config_id = ac.id
                    JOIN trades t ON ah.trade_id = t.id
                    JOIN wallets w ON ah.wallet_address = w.address
                    WHERE ah.status = 'queued'
                    ORDER BY ah.sent_at ASC
                    LIMIT 10
                """)
                
                alerts = cursor.fetchall()
                
                for alert_id, config_id, wallet, trade_id, chat_id, \
                    token_addr, token_name, token_symbol, sol_amount, \
                    score, total, wins, losses in alerts:
                    
                    win_rate = (wins / total * 100) if total > 0 else 0
                    
                    trade_data = {
                        'token_address': token_addr,
                        'token_name': token_name,
                        'token_symbol': token_symbol,
                        'amount_sol': sol_amount,
                        'wallet_score': score,
                        'win_rate': win_rate,
                        'total_trades': total,
                        'wins': wins,
                        'losses': losses
                    }
                    
                    success = await self.send_buy_alert(chat_id, wallet, trade_data)
                    
                    # Update alert status
                    status = 'sent' if success else 'failed'
                    cursor.execute("""
                        UPDATE alert_history SET status = ? WHERE id = ?
                    """, (status, alert_id))
                
                conn.commit()
                conn.close()
                
            except Exception as e:
                logger.error(f"Error processing alerts: {e}")
            
            await asyncio.sleep(2)  # Check every 2 seconds
    
    async def start(self):
        """Start the bot and alert processor"""
        self.init_bot()
        
        # Start alert processing task
        asyncio.create_task(self.process_alert_queue())
        
        # Start the bot
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()
        
        logger.info("Telegram bot is running...")
        
        # Keep running
        await asyncio.Event().wait()

if __name__ == "__main__":
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("❌ Error: TELEGRAM_BOT_TOKEN environment variable not set")
        exit(1)
    
    bot = TelegramAlertBot(token)
    asyncio.run(bot.start())
