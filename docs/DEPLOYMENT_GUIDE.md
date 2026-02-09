# Smart Money Tracker - Deployment Guide

## System Overview

You've built a complete wallet tracking system that:
- Monitors pump.fun trades in real-time via WebSocket
- Tracks wallet performance and calculates scores (0-100)
- Sends Telegram alerts when high-performing wallets buy
- Provides web dashboard to view leaderboard

## Requirements

### Python Packages
```bash
pip install websockets python-telegram-bot fastapi uvicorn
```

### Environment Variables
```bash
export TELEGRAM_BOT_TOKEN="your_bot_token_from_botfather"
```

## Files Created

### Core System
- `data/smart_money_tracker_schema.sql` - Database schema
- `code/smart_money_monitor.py` - WebSocket monitor + scoring engine
- `code/telegram_alert_bot.py` - Telegram bot for alerts
- `code/web_dashboard.py` - Web interface (FastAPI)
- `code/test_system.py` - System validation test

### Documentation
- `docs/smart_money_tracker_architecture.md` - Full technical architecture
- `docs/DEPLOYMENT_GUIDE.md` - This file

## Deployment Steps

### 1. Install Dependencies

```bash
# On your VPS or local machine
pip install websockets python-telegram-bot fastapi uvicorn jinja2
```

### 2. Initialize Database

The database is auto-created on first run, but you can verify schema:

```bash
sqlite3 data/smart_money_tracker.db < data/smart_money_tracker_schema.sql
```

### 3. Start the Monitor (Background)

This collects trade data 24/7:

```bash
# Run in background with nohup
nohup python code/smart_money_monitor.py > logs/monitor.log 2>&1 &

# Or use systemd service (recommended for production)
```

### 4. Create Telegram Bot

1. Message @BotFather on Telegram
2. Create bot: `/newbot`
3. Copy the token
4. Set environment variable:
   ```bash
   export TELEGRAM_BOT_TOKEN="your_token_here"
   ```

### 5. Start Telegram Bot (Background)

```bash
nohup python code/telegram_alert_bot.py > logs/telegram.log 2>&1 &
```

### 6. Start Web Dashboard (Optional)

```bash
# Development
python code/web_dashboard.py

# Production with uvicorn
uvicorn code.web_dashboard:app --host 0.0.0.0 --port 8000 --workers 2
```

Access at: `http://your-server-ip:8000`

## Testing

### Quick Validation (5 minutes)

```bash
python code/test_system.py
```

This runs the monitor for 5 minutes and reports:
- Trade collection rate
- Wallet discovery
- Position tracking
- Scoring system status
- Alert readiness

### Full Test (24 hours recommended)

Let the monitor run for 24 hours to:
- Collect enough trades for meaningful scores
- Identify high-performing wallets
- Populate the leaderboard
- Enable quality alerts

## User Flow

### For Beta Testers

1. **Find your bot on Telegram** - Search for your bot name
2. **Start tracking**:
   ```
   /start
   /leaderboard
   /track <wallet_address>
   ```
3. **Receive alerts** when tracked wallets buy tokens
4. **Check web dashboard** at your deployed URL

### Alert Example

When a tracked wallet buys:
```
🚀 SMART MONEY BUY ALERT

💎 Token: $PEPE
Amount: 5.2 SOL (~$1,040)

📊 Wallet Stats:
Score: 87/100
Win Rate: 73% (22W/8L)
Total Trades: 30

🔗 Buy on pump.fun: [link]
```

## Production Considerations

### Process Management

Use systemd for production deployment:

**monitor.service:**
```ini
[Unit]
Description=Smart Money Monitor
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/project
ExecStart=/usr/bin/python3 code/smart_money_monitor.py
Restart=always

[Install]
WantedBy=multi-user.target
```

**telegram-bot.service:**
```ini
[Unit]
Description=Smart Money Telegram Bot
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/project
Environment="TELEGRAM_BOT_TOKEN=your_token"
ExecStart=/usr/bin/python3 code/telegram_alert_bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable monitor.service telegram-bot.service
sudo systemctl start monitor.service telegram-bot.service
```

### Monitoring

Check logs:
```bash
journalctl -u monitor.service -f
journalctl -u telegram-bot.service -f
```

### Database Backup

```bash
# Daily backup
sqlite3 data/smart_money_tracker.db ".backup data/backup_$(date +%Y%m%d).db"
```

### Nginx Reverse Proxy (for web dashboard)

```nginx
server {
    listen 80;
    server_name smartmoneytracker.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Scaling

### Phase 1 (MVP) - Single Server
- 1 VPS (4GB RAM, 2 CPU)
- SQLite database
- Handles ~1000 active users

### Phase 2 (Growth) - When you hit 1000+ users
- Migrate to PostgreSQL
- Separate alert service to dedicated server
- Add Redis for caching
- Use CDN for web dashboard

## Monetization Setup

### Free Tier Limits
Edit `telegram_alert_bot.py`:
- Track up to 3 wallets per user
- 5 alerts per day limit

### Pro Tier ($49/month)
Implement payment gateway:
- Stripe integration
- User database with subscription status
- Remove limits for paid users

### Track Subscriptions
Add to schema:
```sql
CREATE TABLE subscriptions (
    user_id TEXT PRIMARY KEY,
    tier TEXT DEFAULT 'free',
    stripe_customer_id TEXT,
    subscription_expires INTEGER
);
```

## Success Metrics

### Week 1 Goals
- ✓ System running 24/7 without crashes
- ✓ 10+ high-performing wallets identified
- ✓ Alert latency <5 seconds
- ✓ 5+ beta users tracking wallets

### Month 1 Goals
- 50+ active users
- 10+ paying Pro users ($490 MRR)
- 90%+ alert accuracy (no spam)
- Feature requests from users

### Month 3 Goals
- 200+ active users
- 50+ paying users ($2,450 MRR)
- Premium tier features developed
- Profitable operation

## Troubleshooting

### Monitor not collecting trades
- Check WebSocket connection: `logs/monitor.log`
- Verify pump.fun WebSocket URL is correct
- Test connection manually with `wscat -c wss://pumpportal.fun/api/data`

### No alerts being sent
- Verify TELEGRAM_BOT_TOKEN is set
- Check bot is running: `ps aux | grep telegram`
- Look for queued alerts: `SELECT * FROM alert_history WHERE status='queued'`

### Low performance scores
- System needs 24h+ of data
- Wallets need 5+ completed trades to score
- Bear market = lower scores overall (expected)

### Database locked errors
- SQLite can't handle concurrent writes well
- Migrate to PostgreSQL if you see this frequently

## Next Steps

1. **Run test**: `python code/test_system.py`
2. **Deploy monitor** and let it collect data for 24h
3. **Set up Telegram bot** and test with yourself
4. **Launch to 5 beta users** for feedback
5. **Iterate** based on what they want
6. **Add payment** when you have 10+ users asking for more features

## Support

For questions or issues:
- Check logs first
- Review architecture doc
- Test with `test_system.py`

**You now have a complete, deployable product. Time to validate with real users.**
