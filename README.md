# Nexus Terminal

An AI-native financial intelligence terminal: live prices, sentiment-scored news, SEC filings,
a grounded AI analyst brief, natural-language Q&A, and a company knowledge graph (subsidiaries,
federal contracts, news-derived relationships) — for any ticker.

## Architecture

- **Backend** — `backend/`, FastAPI (Python). Combines Finnhub (price, news), Marketaux
  (supplementary news, broader source coverage), Alpha Vantage (fundamentals, OHLC chart),
  SEC EDGAR (filings, subsidiaries), USASpending.gov (federal contracts), and Claude
  (sentiment, briefs, Q&A, entity/relationship extraction).
- **Frontend** — `frontend/`, Next.js/TypeScript/Tailwind. Dashboard UI + D3 graph visualization.
- **Graph database** — `arcadedb/`, [ArcadeDB](https://arcadedb.com) (self-hosted, free, Cypher-compatible).
  Stores the company knowledge graph.
- **SQLite** (`backend/nexus.db`) — everything else: caching, watchlist, price history.

## Running locally

Three processes, each in its own terminal:

```sh
# 1. Graph database (start first — backend/graph endpoint needs it)
cd nexus-terminal/arcadedb
env 'arcadedb.server.rootPassword=<see backend/.env ARCADEDB_PASSWORD>' ./arcadedb-server.exe

# 2. Backend
cd nexus-terminal/backend
venv\Scripts\python -m uvicorn main:app --port 8000

# 3. Frontend
cd nexus-terminal/frontend
npm run dev
```

Then open http://localhost:3000. Backend API docs: http://localhost:8000/docs. ArcadeDB Studio:
http://localhost:2480.

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

## Cost

Runs comfortably under $50/month at personal-use volume — the only real cost is Claude API
usage (a few dollars/month for typical use). Everything else (Alpha Vantage, Finnhub,
Marketaux, SEC EDGAR, USASpending.gov, ArcadeDB self-hosted) is free.

News is cached per ticker (`NEWS_TTL_HOURS` in `backend/db/models.py`, default 2h) so repeat
searches don't re-hit Finnhub/Marketaux or re-run sentiment scoring — this matters most for
Marketaux's tight 100 req/day free-tier ceiling.
