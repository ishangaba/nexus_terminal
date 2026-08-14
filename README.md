# Nexus Terminal

An AI-native financial intelligence terminal: live prices, sentiment-scored news, SEC filings,
a grounded AI analyst brief, natural-language Q&A, a decisive trade-signal engine with outcome
tracking, and a company knowledge graph (subsidiaries, federal contracts, news-derived
relationships) — for any ticker.

## Architecture

- **Backend** — `backend/`, FastAPI (Python). Combines Finnhub (price, news), Marketaux
  (supplementary news, broader source coverage), Alpha Vantage (fundamentals, OHLC chart),
  SEC EDGAR (filings, subsidiaries), USASpending.gov (federal contracts), and Claude
  (sentiment, briefs, Q&A, trade signals, entity/relationship extraction). Model choice is
  tiered by stakes/volume: Claude Opus 5 for the trade-signal engine (the highest-stakes calls
  in the app — see [Trade Signal](#trade-signal) below), Claude Sonnet 5 for the analyst brief,
  general Q&A, and graph insights, and Claude Haiku 4.5 for high-volume cheap work (news
  sentiment scoring, subsidiary/relationship extraction). See `backend/services/claude_analyst.py`.
- **Frontend** — `frontend/`, Next.js/TypeScript/Tailwind. Dashboard UI + D3 graph visualization.
- **Graph database** — `arcadedb/`, [ArcadeDB](https://arcadedb.com) (self-hosted, free, Cypher-compatible).
  Stores the company knowledge graph.
- **SQLite** (`backend/nexus.db`) — everything else: caching, watchlist, price history,
  portfolio positions, trade signal history.

## Running locally

Three processes, each in its own terminal.

**macOS / Linux:**

```sh
# 1. Graph database (start first — backend/graph endpoint needs it)
cd nexus-terminal/arcadedb
env 'arcadedb.server.rootPassword=<see backend/.env ARCADEDB_PASSWORD>' bin/server.sh

# 2. Backend
cd nexus-terminal/backend
venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000

# 3. Frontend
cd nexus-terminal/frontend
npm run dev
```

**Windows:**

```sh
# 1. Graph database (start first — backend/graph endpoint needs it)
cd nexus-terminal/arcadedb
env 'arcadedb.server.rootPassword=<see backend/.env ARCADEDB_PASSWORD>' bin/server.bat

# 2. Backend
cd nexus-terminal/backend
venv\Scripts\python -m uvicorn main:app --host 0.0.0.0 --port 8000

# 3. Frontend
cd nexus-terminal/frontend
npm run dev
```

Then open http://localhost:3000. Backend API docs: http://localhost:8000/docs. ArcadeDB Studio:
http://localhost:2480.

**Access from another device on the same network:** `--host 0.0.0.0` on the backend and
`npm run dev`'s own default (it already binds all interfaces and prints a "Network" URL) are
enough — the frontend detects the host it was loaded from and points API calls there instead of
`localhost`, and the backend's CORS config accepts requests from private-network origins. Share
the machine's LAN IP with the "Network" URL Next.js prints, e.g. `http://192.168.1.42:3000`.
This is a personal-network convenience, not authenticated multi-user access — anyone who can
reach the machine on that network can use the app and its configured API keys.

## Required API keys

Set in `backend/.env` (see `backend/.env.example`) before first run, or plug them in later from
the app itself via the gear icon → **API Keys** — that panel saves keys live, with no restart,
and only ever shows a masked preview after saving.

| Key | Where to get it | Free tier | Required? |
|---|---|---|---|
| `ALPHA_VANTAGE_API_KEY` | [alphavantage.co](https://www.alphavantage.co/support/#api-key) | 25 req/day | Yes |
| `FINNHUB_API_KEY` | [finnhub.io](https://finnhub.io/register) | 60 req/min | Yes |
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) | pay-as-you-go | Yes |
| `MARKETAUX_API_KEY` | [marketaux.com/pricing](https://www.marketaux.com/pricing) | 100 req/day, 3 articles/request | No — widens news-source diversity (5,000+ outlets) alongside Finnhub; news still works without it |
| `ARCADEDB_PASSWORD` | set your own on first ArcadeDB run | — | Yes, for the company graph feature |

SEC EDGAR and USASpending.gov need no key.

## Trade Signal

Synthesizes price action, technical indicators (SMA/RSI/MACD/Bollinger Bands), fundamentals,
news sentiment, and SEC filings into one decisive call: bullish/bearish/neutral direction and a
concrete `buy_call` / `buy_put` / `stay_out` action — no hedging, no "consult a financial
advisor." Each generated signal is persisted (`backend/db/models.py`,
`trade_signal` table) so you can:

- **Ask decisive follow-up questions** about a given signal (e.g. "what would change this
  call?") without falling back to the general Q&A's more hedged, advice-averse framing —
  `answer_signal_question` in `backend/services/claude_analyst.py`.
- **Record your own decision** (accepted/rejected) on whether you acted on it.
- **Track the outcome** — either self-reported (correct/incorrect/mixed) or auto-resolved: a
  daily background job (`resolve_pending_signals` in `backend/jobs/poller.py`) compares the
  live price against the price at signal time, 5 calendar days later, for any directional
  (non-`stay_out`) call that hasn't been resolved yet.
- **Feed that track record back into future signals for the same symbol** — when a symbol has
  resolved history, it's included in the context sent to Claude on the next signal generation,
  so the model calibrates against its own real track record for that stock (e.g. it won't
  default to high confidence on a bearish call if past bearish calls there were frequently
  wrong). This is a RAG-style feedback loop, not fine-tuning or retraining — the model itself
  never changes, only what it's shown.

Because it's the highest-stakes synthesis in the app, both signal generation and its follow-up
Q&A run on Claude Opus 5 rather than the Sonnet 5 used elsewhere (see Architecture above).
Repeated follow-up questions about the same signal reuse a prompt-cache breakpoint on the
shared context, so only the first question in a session pays full price for it.

## Cost

Runs comfortably under $50/month at personal-use volume — the only real cost is Claude API
usage (a few dollars/month for typical use, even with Trade Signal's calls on the pricier Opus
5 tier — call volume for that feature is low enough that the model choice barely moves the
total). Everything else (Alpha Vantage, Finnhub, Marketaux, SEC EDGAR, USASpending.gov,
ArcadeDB self-hosted) is free.

News is cached per ticker (`NEWS_TTL_HOURS` in `backend/db/models.py`, default 2h) so repeat
searches don't re-hit Finnhub/Marketaux or re-run sentiment scoring — this matters most for
Marketaux's tight 100 req/day free-tier ceiling.
