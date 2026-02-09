"""
Smart Money Tracker - Web Dashboard
Simple FastAPI web interface for viewing wallet leaderboard and stats
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import sqlite3
import time
from typing import List, Dict, Optional
from datetime import datetime

app = FastAPI(title="Smart Money Tracker")

# Database path
DB_PATH = "data/smart_money_tracker.db"

def get_db():
    """Get database connection"""
    return sqlite3.connect(DB_PATH)

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page with leaderboard"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT address, performance_score, total_trades, wins, losses, 
               total_profit_sol, roi_7d, volume_7d, last_active
        FROM wallets
        WHERE total_trades >= 5
        ORDER BY performance_score DESC
        LIMIT 20
    """)
    
    wallets = []
    for row in cursor.fetchall():
        addr, score, total, wins, losses, profit, roi_7d, vol_7d, last_active = row
        win_rate = (wins / total * 100) if total > 0 else 0
        
        # Format last active
        time_diff = int(time.time()) - last_active
        if time_diff < 3600:
            last_active_str = f"{time_diff // 60}m ago"
        elif time_diff < 86400:
            last_active_str = f"{time_diff // 3600}h ago"
        else:
            last_active_str = f"{time_diff // 86400}d ago"
        
        wallets.append({
            'address': addr,
            'short_addr': f"{addr[:8]}...{addr[-6:]}",
            'score': round(score, 1),
            'total_trades': total,
            'wins': wins,
            'losses': losses,
            'win_rate': round(win_rate, 1),
            'profit': round(profit, 2),
            'roi_7d': round(roi_7d, 1),
            'volume_7d': round(vol_7d, 2),
            'last_active': last_active_str
        })
    
    conn.close()
    
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Smart Money Tracker</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0e27;
            color: #e0e0e0;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        header {{
            text-align: center;
            margin-bottom: 40px;
        }}
        h1 {{
            font-size: 2.5em;
            background: linear-gradient(45deg, #00d4ff, #7b2cbf);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
        }}
        .subtitle {{
            color: #888;
            font-size: 1.1em;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        .stat-card {{
            background: #1a1f3a;
            border: 1px solid #2a3150;
            border-radius: 12px;
            padding: 20px;
            text-align: center;
        }}
        .stat-value {{
            font-size: 2em;
            font-weight: bold;
            color: #00d4ff;
            margin-bottom: 5px;
        }}
        .stat-label {{
            color: #888;
            font-size: 0.9em;
        }}
        table {{
            width: 100%;
            background: #1a1f3a;
            border-radius: 12px;
            overflow: hidden;
            border-collapse: collapse;
        }}
        th {{
            background: #2a3150;
            padding: 15px;
            text-align: left;
            font-weight: 600;
            color: #00d4ff;
            border-bottom: 2px solid #00d4ff;
        }}
        td {{
            padding: 15px;
            border-bottom: 1px solid #2a3150;
        }}
        tr:hover {{
            background: #242945;
        }}
        .rank {{
            font-weight: bold;
            color: #00d4ff;
        }}
        .wallet-addr {{
            font-family: 'Courier New', monospace;
            color: #aaa;
            font-size: 0.9em;
        }}
        .score {{
            font-weight: bold;
            font-size: 1.2em;
        }}
        .score-high {{ color: #00ff88; }}
        .score-med {{ color: #ffd700; }}
        .score-low {{ color: #ff6b6b; }}
        .win-rate {{
            color: #00ff88;
        }}
        .positive {{ color: #00ff88; }}
        .negative {{ color: #ff6b6b; }}
        .btn {{
            display: inline-block;
            padding: 8px 16px;
            background: #7b2cbf;
            color: white;
            text-decoration: none;
            border-radius: 6px;
            font-size: 0.85em;
            transition: all 0.2s;
        }}
        .btn:hover {{
            background: #9d4edd;
            transform: translateY(-2px);
        }}
        footer {{
            text-align: center;
            margin-top: 60px;
            padding-top: 20px;
            border-top: 1px solid #2a3150;
            color: #666;
        }}
        .refresh {{
            text-align: center;
            margin: 20px 0;
        }}
        .refresh-btn {{
            padding: 10px 20px;
            background: #00d4ff;
            color: #0a0e27;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-weight: bold;
        }}
        @media (max-width: 768px) {{
            table {{
                font-size: 0.85em;
            }}
            th, td {{
                padding: 10px 8px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🚀 Smart Money Tracker</h1>
            <p class="subtitle">Track high-performing wallets on pump.fun</p>
        </header>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{len(wallets)}</div>
                <div class="stat-label">Top Wallets</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{sum(w['total_trades'] for w in wallets)}</div>
                <div class="stat-label">Total Trades</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{round(sum(w['profit'] for w in wallets), 1)} SOL</div>
                <div class="stat-label">Combined Profit</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{round(sum(w['win_rate'] for w in wallets) / len(wallets) if wallets else 0, 1)}%</div>
                <div class="stat-label">Avg Win Rate</div>
            </div>
        </div>
        
        <div class="refresh">
            <button class="refresh-btn" onclick="location.reload()">↻ Refresh Data</button>
        </div>
        
        <table>
            <thead>
                <tr>
                    <th>Rank</th>
                    <th>Wallet</th>
                    <th>Score</th>
                    <th>Win Rate</th>
                    <th>Trades</th>
                    <th>Profit</th>
                    <th>ROI 7d</th>
                    <th>Vol 7d</th>
                    <th>Last Active</th>
                    <th>Action</th>
                </tr>
            </thead>
            <tbody>
"""
    
    for i, wallet in enumerate(wallets, 1):
        score_class = 'score-high' if wallet['score'] >= 80 else 'score-med' if wallet['score'] >= 60 else 'score-low'
        profit_class = 'positive' if wallet['profit'] > 0 else 'negative'
        roi_class = 'positive' if wallet['roi_7d'] > 0 else 'negative'
        
        html += f"""
                <tr>
                    <td class="rank">#{i}</td>
                    <td class="wallet-addr">{wallet['short_addr']}</td>
                    <td class="score {score_class}">{wallet['score']}</td>
                    <td class="win-rate">{wallet['win_rate']}%</td>
                    <td>{wallet['total_trades']} ({wallet['wins']}W/{wallet['losses']}L)</td>
                    <td class="{profit_class}">{wallet['profit']:+.2f} SOL</td>
                    <td class="{roi_class}">{wallet['roi_7d']:+.1f}%</td>
                    <td>{wallet['volume_7d']:.2f} SOL</td>
                    <td>{wallet['last_active']}</td>
                    <td><a href="/wallet/{wallet['address']}" class="btn">View</a></td>
                </tr>
"""
    
    html += """
            </tbody>
        </table>
        
        <footer>
            <p>Smart Money Tracker - Real-time wallet performance analytics</p>
            <p style="margin-top: 10px; font-size: 0.9em;">
                Get alerts on Telegram: <a href="https://t.me/your_bot" style="color: #00d4ff;">@SmartMoneyTrackerBot</a>
            </p>
        </footer>
    </div>
</body>
</html>
"""
    
    return HTMLResponse(content=html)

@app.get("/wallet/{address}", response_class=HTMLResponse)
async def wallet_detail(address: str):
    """Detailed wallet view"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Get wallet data
    cursor.execute("""
        SELECT performance_score, total_trades, wins, losses, total_profit_sol,
               avg_hold_time_mins, roi_7d, roi_24h, volume_7d, volume_24h, 
               last_active, first_seen
        FROM wallets
        WHERE address = ?
    """, (address,))
    
    wallet_data = cursor.fetchone()
    if not wallet_data:
        conn.close()
        raise HTTPException(status_code=404, detail="Wallet not found")
    
    score, total, wins, losses, profit, avg_hold, roi_7d, roi_24h, vol_7d, vol_24h, last_active, first_seen = wallet_data
    win_rate = (wins / total * 100) if total > 0 else 0
    
    # Get recent trades
    cursor.execute("""
        SELECT token_symbol, token_name, action, amount_sol, timestamp
        FROM trades
        WHERE wallet_address = ?
        ORDER BY timestamp DESC
        LIMIT 20
    """, (address,))
    
    trades = []
    for row in cursor.fetchall():
        symbol, name, action, sol, ts = row
        trades.append({
            'symbol': symbol,
            'name': name,
            'action': action,
            'sol': round(sol, 2),
            'time': datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')
        })
    
    # Get recent positions
    cursor.execute("""
        SELECT token_symbol, entry_timestamp, exit_timestamp, 
               profit_sol, profit_percent, hold_time_mins, status
        FROM positions
        WHERE wallet_address = ?
        ORDER BY entry_timestamp DESC
        LIMIT 10
    """, (address,))
    
    positions = []
    for row in cursor.fetchall():
        symbol, entry_ts, exit_ts, profit_sol, profit_pct, hold_mins, status = row
        positions.append({
            'symbol': symbol,
            'entry': datetime.fromtimestamp(entry_ts).strftime('%Y-%m-%d %H:%M'),
            'exit': datetime.fromtimestamp(exit_ts).strftime('%Y-%m-%d %H:%M') if exit_ts else 'Open',
            'profit_sol': round(profit_sol, 2) if profit_sol else 0,
            'profit_pct': round(profit_pct, 1) if profit_pct else 0,
            'hold': f"{hold_mins // 60}h {hold_mins % 60}m" if hold_mins else '-',
            'status': status
        })
    
    conn.close()
    
    score_class = 'score-high' if score >= 80 else 'score-med' if score >= 60 else 'score-low'
    
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Wallet Details - Smart Money Tracker</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0e27;
            color: #e0e0e0;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        .back-btn {{
            display: inline-block;
            padding: 8px 16px;
            background: #2a3150;
            color: white;
            text-decoration: none;
            border-radius: 6px;
            margin-bottom: 20px;
        }}
        .wallet-header {{
            background: #1a1f3a;
            border: 1px solid #2a3150;
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 30px;
        }}
        .wallet-addr {{
            font-family: 'Courier New', monospace;
            font-size: 1.1em;
            color: #00d4ff;
            margin-bottom: 20px;
        }}
        .score-badge {{
            display: inline-block;
            font-size: 3em;
            font-weight: bold;
            padding: 20px 40px;
            border-radius: 12px;
            background: #2a3150;
        }}
        .score-high {{ color: #00ff88; }}
        .score-med {{ color: #ffd700; }}
        .score-low {{ color: #ff6b6b; }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }}
        .stat-box {{
            background: #242945;
            padding: 15px;
            border-radius: 8px;
        }}
        .stat-label {{
            color: #888;
            font-size: 0.85em;
            margin-bottom: 5px;
        }}
        .stat-value {{
            font-size: 1.5em;
            font-weight: bold;
            color: #00d4ff;
        }}
        .section {{
            background: #1a1f3a;
            border: 1px solid #2a3150;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
        }}
        h2 {{
            color: #00d4ff;
            margin-bottom: 15px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th {{
            text-align: left;
            padding: 10px;
            border-bottom: 1px solid #2a3150;
            color: #888;
        }}
        td {{
            padding: 10px;
            border-bottom: 1px solid #2a3150;
        }}
        .buy {{ color: #00ff88; }}
        .sell {{ color: #ff6b6b; }}
        .positive {{ color: #00ff88; }}
        .negative {{ color: #ff6b6b; }}
    </style>
</head>
<body>
    <div class="container">
        <a href="/" class="back-btn">← Back to Leaderboard</a>
        
        <div class="wallet-header">
            <div class="wallet-addr">{address}</div>
            <div class="score-badge {score_class}">{score:.1f}/100</div>
            
            <div class="stats-grid">
                <div class="stat-box">
                    <div class="stat-label">Win Rate</div>
                    <div class="stat-value">{win_rate:.1f}%</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Total Trades</div>
                    <div class="stat-value">{total}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">W/L Ratio</div>
                    <div class="stat-value">{wins}/{losses}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Total Profit</div>
                    <div class="stat-value {'positive' if profit > 0 else 'negative'}">{profit:+.2f} SOL</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">ROI 7d</div>
                    <div class="stat-value {'positive' if roi_7d > 0 else 'negative'}">{roi_7d:+.1f}%</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Vol 7d</div>
                    <div class="stat-value">{vol_7d:.2f} SOL</div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h2>📊 Recent Positions</h2>
            <table>
                <thead>
                    <tr>
                        <th>Token</th>
                        <th>Entry</th>
                        <th>Exit</th>
                        <th>Hold Time</th>
                        <th>Profit</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
"""
    
    for pos in positions:
        profit_class = 'positive' if pos['profit_sol'] > 0 else 'negative'
        html += f"""
                    <tr>
                        <td>${pos['symbol']}</td>
                        <td>{pos['entry']}</td>
                        <td>{pos['exit']}</td>
                        <td>{pos['hold']}</td>
                        <td class="{profit_class}">{pos['profit_sol']:+.2f} SOL ({pos['profit_pct']:+.1f}%)</td>
                        <td>{pos['status'].upper()}</td>
                    </tr>
"""
    
    html += """
                </tbody>
            </table>
        </div>
        
        <div class="section">
            <h2>🔥 Recent Trades</h2>
            <table>
                <thead>
                    <tr>
                        <th>Token</th>
                        <th>Action</th>
                        <th>Amount</th>
                        <th>Time</th>
                    </tr>
                </thead>
                <tbody>
"""
    
    for trade in trades:
        action_class = 'buy' if trade['action'] == 'buy' else 'sell'
        html += f"""
                    <tr>
                        <td>${trade['symbol']}</td>
                        <td class="{action_class}">{trade['action'].upper()}</td>
                        <td>{trade['sol']} SOL</td>
                        <td>{trade['time']}</td>
                    </tr>
"""
    
    html += """
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""
    
    return HTMLResponse(content=html)

@app.get("/api/leaderboard")
async def api_leaderboard(limit: int = 20):
    """API endpoint for leaderboard data"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT address, performance_score, total_trades, wins, losses, 
               total_profit_sol, roi_7d, volume_7d, last_active
        FROM wallets
        WHERE total_trades >= 5
        ORDER BY performance_score DESC
        LIMIT ?
    """, (limit,))
    
    wallets = []
    for row in cursor.fetchall():
        addr, score, total, wins, losses, profit, roi_7d, vol_7d, last_active = row
        wallets.append({
            'address': addr,
            'score': round(score, 1),
            'total_trades': total,
            'wins': wins,
            'losses': losses,
            'win_rate': round((wins / total * 100) if total > 0 else 0, 1),
            'profit': round(profit, 2),
            'roi_7d': round(roi_7d, 1),
            'volume_7d': round(vol_7d, 2),
            'last_active': last_active
        })
    
    conn.close()
    return JSONResponse(content={'wallets': wallets})

@app.get("/api/wallet/{address}")
async def api_wallet(address: str):
    """API endpoint for wallet details"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT performance_score, total_trades, wins, losses, total_profit_sol,
               avg_hold_time_mins, roi_7d, roi_24h, volume_7d, volume_24h, last_active
        FROM wallets
        WHERE address = ?
    """, (address,))
    
    data = cursor.fetchone()
    if not data:
        conn.close()
        raise HTTPException(status_code=404, detail="Wallet not found")
    
    wallet = {
        'address': address,
        'score': round(data[0], 1),
        'total_trades': data[1],
        'wins': data[2],
        'losses': data[3],
        'win_rate': round((data[2] / data[1] * 100) if data[1] > 0 else 0, 1),
        'profit': round(data[4], 2),
        'avg_hold_mins': data[5],
        'roi_7d': round(data[6], 1),
        'roi_24h': round(data[7], 1),
        'volume_7d': round(data[8], 2),
        'volume_24h': round(data[9], 2),
        'last_active': data[10]
    }
    
    conn.close()
    return JSONResponse(content={'wallet': wallet})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
