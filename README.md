# Nexus Terminal

An AI-native financial intelligence terminal: live prices, sentiment-scored news, SEC filings,
a grounded AI analyst brief, natural-language Q&A, and a company knowledge graph (subsidiaries,
federal contracts, news-derived relationships) — for any ticker.

## Architecture

- **Backend** — `backend/`, FastAPI (Python). Combines Finnhub (price, news), Alpha Vantage
  (fundamentals, OHLC chart), SEC EDGAR (filings, subsidiaries), USASpending.gov (federal
  contracts), and Claude (sentiment, briefs, Q&A, entity/relationship extraction).
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

## Required API keys (all free tier)

Set in `backend/.env` (see `backend/.env.example`):

| Key | Where to get it | Free tier |
|---|---|---|
| `ALPHA_VANTAGE_API_KEY` | [alphavantage.co](https://www.alphavantage.co/support/#api-key) | 25 req/day |
| `FINNHUB_API_KEY` | [finnhub.io](https://finnhub.io/register) | 60 req/min |
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) | pay-as-you-go |
| `ARCADEDB_PASSWORD` | set your own on first ArcadeDB run | — |

SEC EDGAR and USASpending.gov need no key.

## Cost

Runs comfortably under $50/month at personal-use volume — the only real cost is Claude API
usage (a few dollars/month for typical use). Everything else (Alpha Vantage, Finnhub, SEC
EDGAR, USASpending.gov, ArcadeDB self-hosted) is free.
