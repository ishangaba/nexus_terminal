# Nexus Terminal — Current State

Assessment date: 2026-08-13. Written before any Phase-2+ work began, as a baseline for the
evidence-grounded intelligence platform roadmap (see `target-state.md`, `roadmap.md`).

## 1. What this is today

A single-user, locally-run financial dashboard: FastAPI backend + Next.js frontend + SQLite +
self-hosted ArcadeDB for a company relationship graph. For any ticker it aggregates live price,
fundamentals, a 100-day OHLCV chart, sentiment-scored news, recent SEC filings, and a
subsidiary/contract/competitor graph, then layers three Claude-generated products on top: a
grounded analyst brief, free-form Q&A, and a decisive trade signal with outcome tracking and a
per-symbol track record fed back into future signal generation. A portfolio tracker (long
positions, P&L, sector allocation) and a watchlist round out the app.

Everything runs locally against free-tier external APIs; the only recurring cost is Claude
usage (documented at "a few dollars/month" for personal use).

## 2. Backend architecture

### 2.1 Entry point and wiring

`backend/main.py` — FastAPI app, CORS locked to `http://localhost:3000`, includes 7 routers
(`ticker`, `watchlist`, `ask`, `graph`, `settings`, `portfolio`, `signal`). Startup hook runs
`init_db()`, `apply_settings_overrides()` (layers DB-stored API keys over `.env` defaults), and
`start_scheduler()` (APScheduler `BackgroundScheduler`, in-process, no separate worker).

`backend/config.py` — `pydantic_settings.BaseSettings` reading `.env`; `USER_CONFIGURABLE_KEYS`
tuple lists which settings can be overridden at runtime via the Settings UI without a restart
(currently the 4 provider API keys). `apply_settings_overrides()` also calls
`claude_analyst.reload_client()` so a key change takes effect immediately.

### 2.2 Routers (`backend/routers/`) — all thin, `/api/v1` prefixed except where noted

| Router | Routes | Notes |
|---|---|---|
| `ticker.py` | `GET /ticker/{symbol}`, `GET /ticker/{symbol}/price`, `GET /ticker/search`, `POST /ticker/{symbol}/brief` | `/search` must be registered before `/{symbol}` (path-param greedy-match ordering) |
| `signal.py` | `POST /ticker/{symbol}/signal`, `POST .../signal/{id}/decision`, `POST .../signal/{id}/outcome`, `POST .../signal/{id}/ask`, `GET .../signal/history` | Owns the full trade-signal lifecycle (see §2.6) |
| `ask.py` | `POST /ask/{symbol}` | General Q&A, hedged/advice-averse prompt |
| `graph.py` | `GET /graph/{symbol}`, `POST /graph/{symbol}/insights` | Builds/reads the ArcadeDB subgraph |
| `portfolio.py` | `GET /portfolio`, `POST .../positions`, `POST .../positions/{id}/close`, `DELETE .../positions/{id}` | Long-only; live P&L via Finnhub quotes |
| `watchlist.py` | `GET/POST/DELETE /watchlist` | |
| `settings.py` | `GET/PUT /settings`, `DELETE /settings/{key}` | Masks all key values in responses |

**Notable pattern (technical debt, see §7):** `POST /ticker/{symbol}/brief`, `POST
/ticker/{symbol}/signal`, and `POST /ticker/{symbol}/signal/{id}/ask` all accept
`price`/`fundamentals`/`news`/`filings`/`technical_indicators` **in the request body**, supplied
by the frontend (which got them from an earlier `GET /ticker/{symbol}` call). The backend does
not independently re-fetch or verify this data before handing it to Claude — the frontend is a
trusted intermediary for data that's supposed to ground an AI analysis.

### 2.3 Services (`backend/services/`)

**External data providers** — one thin module per provider, each wrapping `httpx` calls and
raising a shared `ProviderError` via `errors.wrap_httpx_error()` (maps HTTP status → a
user-facing message: 401/403 → bad key, 429 → rate limit, timeout, connection error, generic).
This error-normalization boundary is consistent across every provider and already does
graceful-degradation correctly.

| Module | Provider | Used for |
|---|---|---|
| `finnhub.py` | Finnhub | Live quotes, company news, symbol search |
| `alpha_vantage.py` | Alpha Vantage | Fundamentals (`OVERVIEW`), daily OHLCV (`TIME_SERIES_DAILY`) — **25 req/day free cap, shared across both endpoints; the app's tightest real constraint** |
| `marketaux.py` | Marketaux | Supplementary news (100 req/day, 3 articles/request) |
| `sec_edgar.py` | SEC EDGAR | Recent filings (10-K/10-Q/8-K/Form 4), Exhibit 21 subsidiary text |
| `usa_spending.py` | USASpending.gov | Federal contract awards by recipient name |

**Aggregation and orchestration:**

- `aggregator.py` — `gather_context(symbol)` is the closest thing today to a "data acquisition
  layer": fans out to fundamentals/chart/news/filings concurrently, applies a
  cache-then-fetch-then-upsert pattern per data type (TTLs in `db/models.py`), and returns one
  dict shaped `{symbol, price, fundamentals, chart_data, news, filings, errors}` where `errors`
  is a per-field degradation map rather than an all-or-nothing failure. `get_live_price()` is a
  lightweight price-only variant used for the 10s auto-refresh tick.
- `claude_analyst.py` — every Claude call in the app. Tiered model choice by task stakes:
  `claude-opus-5` for trade-signal generation and its follow-up Q&A (highest stakes — a real
  buy/sell verdict), `claude-sonnet-5` for the brief/general-Q&A/graph-insights, `claude-haiku-4-5`
  for headline sentiment scoring and subsidiary/relationship extraction (high-volume, cheap).
  Uses `.messages.parse()` with Pydantic `output_format` for every structured output
  (`TradeSignal`, `SubsidiaryExtraction`, `RelationshipExtraction`), `.messages.create()` for
  free text. Prompt caching is wired on the two Opus-tier signal functions (`cache_control` on
  the shared context block) — verified live to cut a same-signal follow-up question down to a
  handful of full-price tokens. Every function builds its own JSON payload directly from raw
  provider dicts; there is no shared evidence/finding abstraction between functions today beyond
  the shared `_build_context_payload()` helper.
- `graph.py` — raw Cypher-over-HTTP client for ArcadeDB (`run_cypher()` + typed helper
  functions: `ensure_company`, `ensure_gov_entity`, `link_subsidiary`, `link_contract`,
  `link_news_relationship`, `get_company_subgraph`). No ORM, no connection pooling — matches the
  rest of the app's "thin wrapper" philosophy.
- `graph_builder.py` — orchestrates populating the graph for a symbol: SEC Exhibit-21 text →
  Claude-extracted subsidiary names → `link_subsidiary`; USASpending contracts →
  `link_contract`; recent headlines → Claude-extracted `SUPPLIES_TO`/`COMPETES_WITH`/
  `PARTNERS_WITH` relationships → `link_news_relationship`. Gated by a 7-day staleness check
  (`is_graph_stale`) since subsidiary/contract data barely changes.
- `errors.py` — `ProviderError` + `wrap_httpx_error()`, shared by every provider module.

### 2.4 Database (`backend/db/`)

Raw `sqlite3`, no ORM. `get_connection()` opens a fresh connection per call (fine at this
scale/concurrency); `db/models.py` is ~30 free functions, each following a
fresh-connection-open/try/finally-close pattern. Schema (`database.py`, one `executescript`):

`ticker`, `price_snapshot`, `news_item` (**dead — schema'd and has an insert function,
`insert_news_item`, that is never called anywhere; news is cached as JSON blobs in `news_cache`
instead**), `fundamentals_cache`, `chart_cache`, `watchlist`, `filings_cache`,
`graph_build_cache`, `news_cache`, `position` (portfolio, long-only), `app_settings` (DB-stored
API key overrides), `trade_signal`.

Cache TTLs (`db/models.py`): fundamentals 20h, filings 12h, news 1h (recently tightened from 2h
— see git history), graph rebuild 7 days. Each cache type repeats the same
`get_cached_X`/`upsert_X`/inline-TTL-comparison pattern rather than a shared cache helper —
working but duplicated four times.

`trade_signal` — the existing signal lifecycle table: `direction`, `action`, `confidence`,
`summary`, `reasoning_json`, `key_risks_json`, `price_at_signal`, `user_decision`
(accepted/rejected), `user_outcome` (self-reported correct/incorrect/mixed),
`auto_outcome`/`auto_resolved_at`/`resolution_price` (objective, price-based),
`evaluation_days` (default 5). `get_symbol_track_record()` aggregates
`{resolved_count, correct_count, incorrect_count}` per symbol via `COALESCE(auto_outcome,
user_outcome)` and is fed back into the next `generate_trade_signal()` call as a prompt
addendum — this is a real, working, if minimal, historical-feedback loop already in production.

### 2.5 Scheduled jobs (`backend/jobs/poller.py`)

Single in-process `BackgroundScheduler` with two jobs, each a sync wrapper bridging into
`asyncio.run()`:

- `refresh_watchlist` — every 5 minutes, snapshots live prices for every watchlisted symbol.
- `resolve_pending_signals` — every 24 hours, finds directional (`action != 'stay_out'`) signals
  past their `evaluation_days` window with no `auto_outcome` yet, fetches a fresh quote, and
  marks `correct`/`incorrect` by comparing to `price_at_signal`. **No look-ahead-bias guard is
  explicit/tested today** — the logic is directionally correct (never re-derives or edits a
  signal's original verdict, only appends a resolution), but there's no test enforcing that
  invariant.

### 2.6 The trade-signal lifecycle (most architecturally relevant existing feature)

`generate_trade_signal()` → persisted row → user can `accept`/`reject` (their own decision, an
independent axis from outcome) → outcome resolves either by self-report or the daily job →
`get_symbol_track_record()` feeds resolved history back into the *next* signal for that symbol.
This is functionally a miniature version of the target platform's evidence→thesis→evaluation
loop already, just: (a) not generalized past trade signals to general research questions, (b)
not measuring forward returns/calibration/Brier score, only raw win-rate, (c) not backed by a
normalized evidence model — the payload sent to Claude is raw provider dicts assembled inline.

### 2.7 Knowledge graph

ArcadeDB (self-hosted, Cypher-compatible), reached via raw HTTP + Cypher strings (no driver).
Node types: `Company`, `GovEntity`. Edge types: `SUBSIDIARY_OF` (SEC-sourced),
`HAS_CONTRACT` (USASpending-sourced, carries `amount`/`date`), `SUPPLIES_TO`/`COMPETES_WITH`/
`PARTNERS_WITH` (Claude-inferred from news headlines, carries an `evidence` string).
**Provenance is partial**: contract/news edges carry *some* metadata, but there's no
`confidence` score, no `retrieved_at` timestamp, and — most importantly — no way for a UI or
downstream reasoner to distinguish "SEC-filing-confirmed subsidiary" from "Claude inferred this
from one headline" once the edge exists; both render identically in `GraphView.tsx`. Graph
traversal today is 1-hop only (`get_company_subgraph`); no 2-hop exposure, no portfolio-wide
cross-exposure queries.

## 3. Frontend architecture

Next.js 16 (App Router), React 19, Tailwind v4, TypeScript. `frontend/app/page.tsx` is a single
large client component holding essentially all app-level state (ticker data, brief, graph,
graph insights, watchlist-refresh counter, add-to-watchlist flow, settings-panel visibility) and
orchestrating every data fetch. `frontend/lib/api.ts` is a single ~300-line file holding every
TypeScript interface and every `fetch()` wrapper for the whole app. Both are growing
concentration points — not broken, but will need splitting as new sections (thesis, evidence,
events, calibration) are added.

Components are otherwise well-factored: one file per UI section, consistent props-down
loading/error handling, a consistent visual language (cyan = observed data, violet = AI-
generated content, emerald/rose = gains/losses or bullish/bearish). `lib/indicators.ts` +
`lib/technicalSnapshot.ts` are pure, framework-free technical-indicator math — already exactly
the "deterministic tool, not an LLM call" pattern the target architecture wants, just
implemented client-side rather than backend-owned. `hooks/useAutoRefresh.ts` is a clean,
reusable visibility-aware polling hook (paused when the tab is backgrounded).

Recent additions: a debounced ticker/company-name typeahead (`TickerSearch.tsx`, backed by
Finnhub's `/search`), an animated landing hero (Motion + CSS, `Hero.tsx` /
`AnimatedBackground.tsx` / `TickerTape.tsx`), and a candlestick chart with toggleable SMA/
Bollinger/RSI/MACD overlays (`PriceChart.tsx`, `lightweight-charts`).

## 4. What should be preserved as-is

- **Provider service modules + `ProviderError`/`wrap_httpx_error`** — clean, consistent,
  already does graceful per-provider degradation correctly. A `Protocol`-based interface
  (target Phase 19) can wrap these later without touching their internals.
- **`aggregator.gather_context`** — structurally already a data-acquisition layer: concurrent
  fan-out, per-type caching, per-field degradation. Needs an evidence-normalization step added
  on top, not a rewrite.
- **`claude_analyst.py`'s tiered model strategy** — exactly the cost/stakes discipline the
  target architecture wants. Keep as-is; extend with new functions, don't restructure existing
  ones.
- **The `trade_signal` lifecycle and track-record feedback loop** — a working foundation for
  signal evaluation. Extend with forward-return tracking and calibration; don't replace the
  table or the accept/reject/outcome UX.
- **`graph.py`/`graph_builder.py`** — sound design (SEC + USASpending + Claude-inferred, each
  through its own link function). Extend with confidence/retrieved_at fields and 2-hop
  traversal; don't rewrite the Cypher client.
- **Frontend visual language and component boundaries.** Explicit product requirement to keep
  the terminal feel — new sections should match, not replace, the existing conventions.
- **`useAutoRefresh`, `lib/indicators.ts`/`technicalSnapshot.ts`** — clean, no changes needed
  (the backend gets its own Python port of the indicator math for server-owned analysis; the
  frontend copy stays for the interactive chart overlays, which are a legitimately
  client-side, non-authoritative visualization concern).
- **The fresh-connection-per-call SQLite pattern.** Correct for this app's scale; no need for
  an ORM or connection pool.

## 5. Technical debt and gaps

1. **No normalized evidence layer.** Every analytical function passes around raw
   provider-shaped dicts. No common envelope carries source/timestamp/confidence/provenance.
2. **Frontend-supplied "authoritative" analysis inputs.** `brief`, `signal`, and `signal/ask`
   accept price/fundamentals/news/filings/technical-indicators from the request body rather
   than the backend independently sourcing (or at minimum verifying) them.
3. **No orchestration/tool-routing layer.** Each Claude-analyst function re-implements
   "assemble a data shape → hand it entirely to Claude to reason over." No deterministic
   pre-processing splits out what doesn't need an LLM (technical-indicator interpretation,
   basic news dedup/clustering) from what does (semantic synthesis).
4. **Signal evaluation is win-rate only.** No forward-return tracking (1d/3d/5d/10d/20d), no
   benchmark-relative return, no confidence-bucketed calibration, no Brier score, no MFE/MAE.
5. **Partial graph provenance.** No `confidence` or `retrieved_at` on edges; no UI/API
   distinction between confirmed (SEC/USASpending-sourced) and inferred (Claude-derived from
   news) relationships. No 2-hop traversal or portfolio-wide exposure queries.
6. **Dead code**: `news_item` table + `insert_news_item()`, never called.
7. **Zero automated tests.** No pytest, no test files, anywhere in the repo, backend or
   frontend.
8. **No structured observability.** Only ad-hoc `logger.exception` in two files. No request
   IDs, latency timing, cache hit/miss tracking, or per-tool/per-provider cost accounting.
9. **`page.tsx` and `lib/api.ts` are both large, single-file concentration points** that will
   need splitting as new sections (thesis, evidence, events, calibration, portfolio
   intelligence) are added.
10. **No explicit look-ahead-bias guard** on signal resolution — the current logic is correct
    by inspection but untested, and there's no invariant preventing a future change from
    accidentally mutating a signal's original verdict after the fact.
11. **Security, at personal-local-app scale, is reasonable but minimal**: API keys are kept
    server-side and masked in responses (good); CORS is hardcoded to one localhost origin (fine
    for personal use, no environment-based prod config); no rate limiting of any kind (relies
    entirely on upstream providers' own limits); no request-size validation; ticker path
    parameters aren't format-validated before being interpolated into provider URLs (low risk —
    `httpx` params are properly encoded — but unvalidated); Settings endpoints have no auth
    (acceptable for single-user localhost, a real gap if ever exposed beyond that).
12. **Model and provider coupling.** `claude_analyst.py` calls the `anthropic` SDK directly
    throughout (no `IntelligenceModel` abstraction); `aggregator.py` calls provider modules by
    name (no `MarketDataProvider`/`NewsProvider` `Protocol`). Both are real but low-priority —
    this is a single-provider hobby app today, and forcing an abstraction before there's a
    second implementation would be premature.

## 6. Summary

The foundation is sound: consistent error handling, real graceful degradation, sensible
model-tiering, a genuinely working (if minimal) signal-evaluation loop, and a graph that already
distinguishes evidence types even if it doesn't yet score their confidence. The gaps are exactly
what you'd expect from a project that grew by adding features incrementally rather than
designing the evidence/orchestration layer up front: no shared `Evidence` abstraction, no tool
decomposition, no calibration math, no tests, no observability. None of it requires a rewrite —
it requires adding a normalization and orchestration layer *on top of* what's already there. See
`target-state.md` for the proposed architecture and `roadmap.md` for how to get there
incrementally.
