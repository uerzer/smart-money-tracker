"""
Smart Money Tracker - System Test
Run monitor for a short period and validate data quality
"""

import asyncio
import sqlite3
import time
from smart_money_monitor import SmartMoneyTracker
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SystemTester:
    def __init__(self):
        self.tracker = SmartMoneyTracker()
        self.start_time = time.time()
        self.test_duration = 300  # 5 minutes
        
    async def run_test(self):
        """Run monitoring for test duration"""
        logger.info(f"Starting {self.test_duration}s test run...")
        
        # Create task for monitoring
        monitor_task = asyncio.create_task(self.tracker.monitor())
        
        # Create task for periodic stats reporting
        stats_task = asyncio.create_task(self.report_stats())
        
        # Wait for test duration
        await asyncio.sleep(self.test_duration)
        
        # Cancel tasks
        monitor_task.cancel()
        stats_task.cancel()
        
        # Final report
        await self.final_report()
    
    async def report_stats(self):
        """Report stats every 30 seconds"""
        while True:
            await asyncio.sleep(30)
            
            elapsed = int(time.time() - self.start_time)
            conn = sqlite3.connect(self.tracker.db_path)
            cursor = conn.cursor()
            
            # Get counts
            cursor.execute("SELECT COUNT(*) FROM trades")
            total_trades = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM wallets")
            total_wallets = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM positions WHERE status = 'open'")
            open_positions = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM positions WHERE status = 'closed'")
            closed_positions = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM wallets WHERE performance_score > 0")
            scored_wallets = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT COUNT(*) FROM wallets 
                WHERE total_trades >= 5 AND performance_score >= 70
            """)
            high_performers = cursor.fetchone()[0]
            
            conn.close()
            
            logger.info(f"\n{'='*50}")
            logger.info(f"STATS @ {elapsed}s")
            logger.info(f"Trades: {total_trades}")
            logger.info(f"Unique Wallets: {total_wallets}")
            logger.info(f"Open Positions: {open_positions}")
            logger.info(f"Closed Positions: {closed_positions}")
            logger.info(f"Scored Wallets: {scored_wallets}")
            logger.info(f"High Performers (score ≥70): {high_performers}")
            logger.info(f"{'='*50}\n")
    
    async def final_report(self):
        """Generate final test report"""
        logger.info("\n" + "="*60)
        logger.info("FINAL TEST REPORT")
        logger.info("="*60)
        
        conn = sqlite3.connect(self.tracker.db_path)
        cursor = conn.cursor()
        
        # Overall stats
        cursor.execute("SELECT COUNT(*) FROM trades")
        total_trades = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM wallets")
        total_wallets = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM positions WHERE status = 'closed'")
        closed_positions = cursor.fetchone()[0]
        
        # Get top 5 wallets
        cursor.execute("""
            SELECT address, performance_score, total_trades, wins, losses, total_profit_sol
            FROM wallets
            WHERE total_trades >= 3
            ORDER BY performance_score DESC
            LIMIT 5
        """)
        
        top_wallets = cursor.fetchall()
        
        # Alert readiness check
        cursor.execute("""
            SELECT COUNT(*) FROM wallets 
            WHERE total_trades >= 5 AND performance_score >= 70
        """)
        alert_ready = cursor.fetchone()[0]
        
        logger.info(f"\n📊 COLLECTION STATS:")
        logger.info(f"Total Trades: {total_trades}")
        logger.info(f"Unique Wallets: {total_wallets}")
        logger.info(f"Closed Positions: {closed_positions}")
        logger.info(f"Alert-Ready Wallets (score ≥70, trades ≥5): {alert_ready}")
        
        if top_wallets:
            logger.info(f"\n🏆 TOP 5 WALLETS:")
            for i, (addr, score, trades, wins, losses, profit) in enumerate(top_wallets, 1):
                win_rate = (wins / trades * 100) if trades > 0 else 0
                logger.info(f"{i}. {addr[:8]}...{addr[-6:]}")
                logger.info(f"   Score: {score:.1f} | WR: {win_rate:.1f}% | Trades: {trades} | Profit: {profit:.2f} SOL")
        
        # System health checks
        logger.info(f"\n✅ SYSTEM HEALTH:")
        
        issues = []
        
        if total_trades == 0:
            issues.append("❌ No trades collected - WebSocket may not be working")
        else:
            logger.info(f"✓ WebSocket collecting trades ({total_trades} collected)")
        
        if closed_positions == 0 and total_trades > 100:
            issues.append("⚠️  No closed positions - wallets may not be selling yet")
        else:
            logger.info(f"✓ Position tracking working ({closed_positions} closed)")
        
        if alert_ready == 0 and total_trades > 100:
            issues.append("⚠️  No alert-ready wallets yet - need more data or better performers")
        elif alert_ready > 0:
            logger.info(f"✓ Alert system ready ({alert_ready} trackable wallets)")
        
        # Database integrity check
        cursor.execute("""
            SELECT COUNT(*) FROM trades t
            LEFT JOIN wallets w ON t.wallet_address = w.address
            WHERE w.address IS NULL
        """)
        orphaned_trades = cursor.fetchone()[0]
        
        if orphaned_trades > 0:
            issues.append(f"❌ {orphaned_trades} orphaned trades (missing wallet records)")
        else:
            logger.info(f"✓ Database integrity good")
        
        if issues:
            logger.info(f"\n⚠️  ISSUES DETECTED:")
            for issue in issues:
                logger.info(f"  {issue}")
        
        # Next steps
        logger.info(f"\n📋 NEXT STEPS:")
        if total_trades < 100:
            logger.info("1. Run monitor longer to collect more data (24h recommended)")
        if alert_ready == 0:
            logger.info("2. Wait for wallets to complete more trades to calculate scores")
        if alert_ready > 0:
            logger.info("1. ✅ Ready to test Telegram alerts!")
            logger.info("2. Start telegram_alert_bot.py")
            logger.info("3. Use /leaderboard command to see top wallets")
            logger.info("4. Use /track command to start receiving alerts")
        
        logger.info(f"\n🌐 WEB DASHBOARD:")
        logger.info("Start with: python code/web_dashboard.py")
        logger.info("View at: http://localhost:8000")
        
        logger.info("="*60 + "\n")
        
        conn.close()

async def main():
    tester = SystemTester()
    try:
        await tester.run_test()
    except KeyboardInterrupt:
        logger.info("\nTest interrupted by user")
        await tester.final_report()

if __name__ == "__main__":
    asyncio.run(main())
