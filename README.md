# CounterTrade Bot

A local-first **contrarian emotional risk manager** for traders. It monitors your trading messages, detects emotionally charged states, and provides counter-sentiment decision support to help you avoid impulsive trades.

## How It Works

```
Your Message → Emotion Detection → State Inference → Decision Engine → Contrarian Recommendation
```

### Emotion Detection
The bot analyzes your text and classifies:
- **Primary emotion**: anger, despair, panic, FOMO, greed, euphoria, fear, etc.
- **Secondary emotion**: supporting emotional signal
- **Intensity** (0–100): how strong the emotion is
- **Confidence** (0–100): how certain the classification is

### Trading State Inference
Maps emotions to trading states:
- Capitulation, Panic-selling, Revenge-trading, FOMO-chasing
- Greed-top, Tilted/Impaired, Calm/Neutral, Disciplined, Uncertain

### Contrarian Decision Engine
Uses configurable rules to generate recommendations:

| Your State | Bot Leans Toward |
|---|---|
| Panic + selling urge | WAIT / don't market-sell |
| Despair + capitulation | BUY / reduce selling |
| FOMO + chasing pump | WAIT / don't chase |
| Greed + euphoria | REDUCE / take profit |
| Anger + revenge | NO TRADE + cooldown |
| Overconfidence | REDUCE size |
| Exhaustion / tilt | NO TRADE + long cooldown |
| Calm / disciplined | Trust your own analysis |

### Guardrails
- Cooldown periods after anger/revenge/tilt detection
- "Document thesis first" before high-conviction actions
- Max position-size warnings
- Confidence threshold below which recommendation is HOLD/WAIT
- Explicit note that emotional inversion is a heuristic, not an edge

## Setup

### Prerequisites
- Python 3.10+
- Node.js 18+ (for frontend)
- (Optional) Ollama or LM Studio for local LLM support

### Install & Run

```bash
# Clone and enter the project
cd tradingbotforme

# Install Python dependencies
pip install -r requirements.txt

# Start the backend (with seed data on first run)
python run.py --seed

# In another terminal, start the frontend
cd frontend
npm install
npm run dev
```

The backend runs on `http://localhost:8000` and the frontend on `http://localhost:3000`.

### With Local LLM (Optional)

1. Install [Ollama](https://ollama.ai) and pull a model:
   ```bash
   ollama pull llama3.2
   ```
2. Edit `config/settings.json` and set `"use_llm": true`
3. The bot will use the LLM for richer emotion analysis and recommendations

Without an LLM, the bot uses a robust keyword-based emotion detection system that works well for common trading language.

## Usage

### Chat Tab
Type your trading thoughts, feelings, or impulses. Include as much context as you want. The bot will analyze your emotional state and provide a recommendation.

**Example messages:**
- *"BTC just dropped 20% and I'm about to sell everything. This is it, crypto is dead."*
- *"SOL is pumping 30% and I NEED to get in NOW before it's too late!"*
- *"Just got stopped out again. Going back in with 3x the size. They won't shake me out."*
- *"Looking at ETH, consolidating near support with declining volume. Planning 2% risk trade to $4000."*

### Market Context Form
Optionally fill in:
- Asset, price, recent move %
- Position size, unrealized P/L
- Thesis and invalidation level

This helps the bot give more contextual recommendations.

### Journal
All analyses are stored. Review past entries to:
- Rate whether the bot was right or wrong
- Track what you actually did vs. what was recommended
- Log P/L outcomes

### Stats
View analytics on:
- Most common emotional states
- Recommendations given vs. actions taken
- P/L by emotional state
- P/L when following the bot vs. not

### Rules Editor
Customize the decision rules in the UI or directly in `config/rules.json`.

## Configuration

### `config/settings.json`
- LLM backend settings (Ollama/LM Studio URL, model name)
- Notification settings (Telegram bot token/chat ID)
- Analysis thresholds

### `config/rules.json`
- Trading rules with conditions, actions, conviction ranges
- Guardrails and cooldown periods
- Priority ordering

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/analyze` | Analyze a message |
| GET | `/api/journal` | List journal entries (with filters) |
| GET | `/api/journal/{id}` | Get single entry |
| PUT | `/api/journal/{id}/review` | Review/rate an entry |
| POST | `/api/journal/{id}/override` | Override recommendation |
| GET | `/api/stats` | Get statistics |
| GET/PUT | `/api/rules` | Get/update rules |
| GET/PUT | `/api/settings` | Get/update settings |
| GET | `/api/health` | Health check |

## Architecture

```
backend/
├── main.py         # FastAPI app and routes
├── models.py       # Pydantic data models
├── database.py     # SQLite via SQLAlchemy
├── emotion.py      # Emotion detection (keyword + LLM)
├── decision.py     # Contrarian decision engine
├── rules.py        # Configurable rule engine
├── llm.py          # Local LLM integration
└── notify.py       # Telegram/desktop notifications
frontend/
└── src/
    ├── App.jsx     # Main app with tab navigation
    ├── api.js      # API client
    └── components/ # UI components
config/
├── rules.json      # Editable trading rules
└── settings.json   # App settings
data/
├── countertrade.db # SQLite database (auto-created)
└── seed.sql        # Sample data
```

## Important Design Principle

This tool is a **contrarian emotional risk manager**, not a hype machine. It challenges you when your emotions are likely driving the decision. It does not place trades, guarantee outcomes, or replace your own analysis. Emotional inversion is a heuristic, not an edge by itself.

## Non-Goals
- No exchange execution or auto-trading
- No real money management
- Not optimized for visual complexity over utility
