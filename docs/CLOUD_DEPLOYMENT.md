# ☁️ Cloud Deployment Guide

## TL;DR: Best Options by Use Case

| Option | Cost | Difficulty | Best For |
|--------|------|------------|----------|
| **Railway** | ~$5-10/mo | Easiest | Quick launch, no DevOps |
| **Render** | ~$7-15/mo | Easy | Similar to Railway, better WebSocket support |
| **DigitalOcean** | $4-6/mo | Medium | Cheapest, full control |
| **Fly.io** | ~$5/mo | Medium | Global edge deployment |

**Recommendation: Start with Railway or Render for speed, migrate to DigitalOcean when you hit 100+ users.**

---

## Option 1: Railway (Easiest - 5 mins)

**Cost:** $5/mo (Hobby plan) + ~$3/mo usage = **~$8/mo total**

**Pros:**
- Zero DevOps - just push code
- Automatic SSL
- Built-in monitoring
- Environment variables UI

**Cons:**
- WebSocket support can be finicky (test first)
- More expensive at scale

### Deploy to Railway

1. **Create account:** https://railway.app
2. **Install Railway CLI:**
```bash
npm install -g @railway/cli
railway login
```

3. **Create new project:**
```bash
cd smart-money-tracker
railway init
```

4. **Add environment variables:**
```bash
railway variables set TELEGRAM_BOT_TOKEN=your_token_here
```

5. **Deploy:**
```bash
railway up
```

6. **Start services:**
   - Railway dashboard → Add service
   - Create 3 services:
     - `monitor` (runs smart_money_monitor.py)
     - `telegram-bot` (runs telegram_alert_bot.py)
     - `dashboard` (runs web_dashboard.py with exposed port 8000)

**Start commands:**
- Monitor: `python code/smart_money_monitor.py`
- Bot: `python code/telegram_alert_bot.py`
- Dashboard: `uvicorn code.web_dashboard:app --host 0.0.0.0 --port $PORT`

**SQLite Warning:** Railway ephemeral storage means database resets on redeploy. Solution:
- Use Railway's persistent volume ($0.15/GB/mo)
- Or migrate to PostgreSQL when you have paying users

---

## Option 2: Render.com (Easy - 10 mins)

**Cost:** $7/mo per service = **$21/mo for 3 services** (monitor, bot, dashboard)

**Pros:**
- Better WebSocket support than Railway
- Free SSL
- Auto-deploys from GitHub
- Persistent disk included

**Cons:**
- More expensive for multiple services
- Services spin down after 15min inactivity on free tier

### Deploy to Render

1. **Create account:** https://render.com
2. **Connect GitHub repo**
3. **Create 3 Web Services:**

**Service 1: Monitor**
- Name: `smart-money-monitor`
- Start Command: `python code/smart_money_monitor.py`
- Plan: Starter ($7/mo)

**Service 2: Telegram Bot**
- Name: `telegram-bot`
- Start Command: `python code/telegram_alert_bot.py`
- Plan: Starter ($7/mo)

**Service 3: Dashboard**
- Name: `dashboard`
- Start Command: `uvicorn code.web_dashboard:app --host 0.0.0.0 --port $PORT`
- Plan: Starter ($7/mo)

4. **Add environment variables** (same for all 3 services):
   - `TELEGRAM_BOT_TOKEN`: your_token
   - `DB_PATH`: `/opt/render/project/data/smart_money_tracker.db`

5. **Add persistent disk** to monitor service:
   - Mount path: `/opt/render/project/data`
   - Size: 1GB (free)

**Cost optimization:** Run only monitor + bot on Render ($14/mo), self-host dashboard

---

## Option 3: DigitalOcean Droplet (Cheapest - 30 mins)

**Cost:** $4/mo (Basic Droplet) or $6/mo (recommended)

**Pros:**
- Cheapest option
- Full control
- No usage metering
- Predictable costs

**Cons:**
- You manage the server
- Manual updates/monitoring
- Need basic Linux skills

### Deploy to DigitalOcean

1. **Create Droplet:**
   - Go to https://digitalocean.com
   - Create Droplet → Ubuntu 22.04 LTS
   - Size: Basic ($6/mo - 1GB RAM, 1 vCPU)
   - Datacenter: Closest to your users

2. **SSH into server:**
```bash
ssh root@your_droplet_ip
```

3. **Setup environment:**
```bash
# Update system
apt update && apt upgrade -y

# Install Python 3.11+
apt install python3 python3-pip python3-venv git -y

# Clone repo
git clone https://github.com/uerzer/smart-money-tracker.git
cd smart-money-tracker

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create data directory
mkdir -p data
```

4. **Configure environment variables:**
```bash
nano .env
```
Add:
```
TELEGRAM_BOT_TOKEN=your_token_here
DB_PATH=data/smart_money_tracker.db
```

5. **Create systemd services** (run 24/7):

**Monitor service:**
```bash
nano /etc/systemd/system/smart-money-monitor.service
```
```ini
[Unit]
Description=Smart Money Monitor
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/smart-money-tracker
Environment=PATH=/root/smart-money-tracker/venv/bin
ExecStart=/root/smart-money-tracker/venv/bin/python code/smart_money_monitor.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Telegram bot service:**
```bash
nano /etc/systemd/system/telegram-bot.service
```
```ini
[Unit]
Description=Telegram Alert Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/smart-money-tracker
Environment=PATH=/root/smart-money-tracker/venv/bin
ExecStart=/root/smart-money-tracker/venv/bin/python code/telegram_alert_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Dashboard service:**
```bash
nano /etc/systemd/system/web-dashboard.service
```
```ini
[Unit]
Description=Web Dashboard
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/smart-money-tracker
Environment=PATH=/root/smart-money-tracker/venv/bin
ExecStart=/root/smart-money-tracker/venv/bin/uvicorn code.web_dashboard:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

6. **Start services:**
```bash
systemctl daemon-reload
systemctl enable smart-money-monitor telegram-bot web-dashboard
systemctl start smart-money-monitor telegram-bot web-dashboard
```

7. **Check status:**
```bash
systemctl status smart-money-monitor
systemctl status telegram-bot
systemctl status web-dashboard
```

8. **View logs:**
```bash
journalctl -u smart-money-monitor -f
journalctl -u telegram-bot -f
journalctl -u web-dashboard -f
```

9. **Setup nginx (optional - for custom domain):**
```bash
apt install nginx -y
nano /etc/nginx/sites-available/smart-money-tracker
```
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```
```bash
ln -s /etc/nginx/sites-available/smart-money-tracker /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
```

10. **SSL with Let's Encrypt:**
```bash
apt install certbot python3-certbot-nginx -y
certbot --nginx -d your-domain.com
```

---

## Option 4: Fly.io (Developer-Friendly - 20 mins)

**Cost:** ~$5/mo (256MB RAM per service)

**Pros:**
- Global edge network
- Great WebSocket support
- Free SSL
- Generous free tier

**Cons:**
- More complex config
- Billing can be confusing

### Deploy to Fly.io

1. **Install flyctl:**
```bash
curl -L https://fly.io/install.sh | sh
```

2. **Login:**
```bash
flyctl auth login
```

3. **Launch apps** (do this 3 times - monitor, bot, dashboard):

**Monitor:**
```bash
flyctl launch --name smart-money-monitor --no-deploy
```
Edit `fly.toml`:
```toml
app = "smart-money-monitor"
primary_region = "iad"

[build]
  builder = "paketobuildpacks/builder:base"

[env]
  PORT = "8080"

[[services]]
  internal_port = 8080
  protocol = "tcp"

[mounts]
  source = "smart_money_data"
  destination = "/data"
```

**Deploy:**
```bash
flyctl volumes create smart_money_data --size 1
flyctl secrets set TELEGRAM_BOT_TOKEN=your_token
flyctl deploy
```

Repeat for bot and dashboard services.

---

## Cost Comparison (Monthly)

| Provider | Basic Setup | With Dashboard | Notes |
|----------|-------------|----------------|-------|
| **Railway** | $8 | $12 | Easiest, potential WebSocket issues |
| **Render** | $14 | $21 | Most reliable, auto-scaling |
| **DigitalOcean** | $6 | $6 | Cheapest, DIY |
| **Fly.io** | $5 | $10 | Best global performance |

---

## Recommendation for You

**Phase 1 (Beta - Week 1-2):** 
- **Use Railway or Render** (~$10-15/mo)
- Get 5-20 beta users
- Validate the product works
- No DevOps overhead

**Phase 2 (Launch - Month 1):**
- Stay on Railway/Render until 50+ users
- Revenue: $2,450/mo (50 users × $49)
- Cost: $15/mo = **99.4% profit margin**

**Phase 3 (Scale - Month 2+):**
- Migrate to **DigitalOcean $12/mo droplet** (2GB RAM)
- Or upgrade to **DigitalOcean $24/mo** (4GB RAM) for 500+ users
- Revenue: $24,500/mo (500 users)
- Cost: $24/mo = **99.9% profit margin**

**Phase 4 (Enterprise - Month 6+):**
- Multiple DigitalOcean droplets with load balancing
- PostgreSQL managed database ($15/mo)
- Redis for caching ($10/mo)
- Total infrastructure: ~$100/mo
- Revenue: $49K+/mo
- Cost: <0.3% of revenue

---

## Quick Start (Choose Your Path)

### Path A: Fast Launch (Railway)
```bash
npm install -g @railway/cli
railway login
railway init
railway up
```
**Live in 5 minutes.**

### Path B: Cheapest (DigitalOcean)
```bash
# SSH into droplet
ssh root@your_ip

# One-line setup
curl -s https://raw.githubusercontent.com/uerzer/smart-money-tracker/main/scripts/deploy-digitalocean.sh | bash
```
**Live in 10 minutes, $6/mo.**

### Path C: Production-Ready (Docker)
```bash
docker-compose up -d
```
**Live in 3 minutes (after Docker setup).**

---

## Need Help?

- **Railway Issues:** https://railway.app/help
- **DigitalOcean Guide:** https://docs.digitalocean.com/
- **Server management:** Consider hiring a DevOps freelancer on Upwork ($50-100 one-time setup)

**Bottom line: Don't overthink this. Railway = fastest. DigitalOcean = cheapest. Both work.**