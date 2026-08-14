# Nexus Terminal — Roadmap

Companion to `current-state.md` and `target-state.md`. Each milestone is independently shippable
— the app stays fully runnable after every one, existing functionality is never broken, and
scope is deliberately kept smaller than the original request's full 22-phase spec at any single
step. Do not start a milestone before the previous one's Definition of Done is met.

---

## Milestone 1 — Evidence Foundation

**Goal:** Prove the evidence → tools → orchestrator → thesis architecture end to end with the
smallest real vertical slice, without touching any existing route, table, or frontend file.

**Flow:** `GET/POST ticker request → existing aggregator.gather_context() → Evidence adapters →
Technical Tool + News Tool (deterministic) → Research Orchestrator (always-run, no routing yet)
→ Claude synthesis (evidence-grounded, not raw dicts) → ResearchThesis → POST
/api/research/{ticker}`.

**New files:**
- `backend/intelligence/__init__.py`, `models/__init__.py`, `tools/__init__.py`
- `backend/intelligence/models/evidence.py` — `Evidence`, `EvidenceType`
- `backend/intelligence/models/findings.py` — `AnalyticalFinding`
- `backend/intelligence/models/thesis.py` — `ResearchThesis`
- `backend/intelligence/evidence_adapters.py` — turns `gather_context()`'s dict output into
  `list[Evidence]`
- `backend/intelligence/tools/technical_tool.py` — Python port of
  `frontend/lib/indicators.ts` (SMA/RSI/MACD/Bollinger), deterministic finding synthesis, no
  LLM call
- `backend/intelligence/tools/news_tool.py` — dedup (already partly done in `aggregator.py`,
  consolidate here) + recency weighting + aggregate from existing per-headline sentiment scores,
  deterministic finding synthesis, no new LLM call
- `backend/intelligence/orchestrator.py` — `run_research(ticker) -> ResearchThesis`
- `backend/routers/research.py` — `POST /api/research/{ticker}`

**Modified files:**
- `backend/services/claude_analyst.py` — add `synthesize_research(ticker, findings, evidence) ->
  ResearchThesis` and its system prompt (new function; every existing function untouched)
- `backend/main.py` — register the new router (one line)

**Database migrations:** none. Evidence/Findings/Thesis are constructed in-memory per request.

**API changes:** additive only — `POST /api/research/{ticker}`.

**Frontend changes:** none. Verified via direct API calls; wiring a UI is Milestone 3.

**Tests:** manual curl verification for Milestone 1 (matches the rest of the app's current
testing posture — see Milestone 7 for when automated tests are introduced project-wide, so
Milestone 1 doesn't have to invent a test harness in isolation).

**Risks:** Claude synthesis prompt could re-introduce ungrounded claims if not tightly scoped to
the given findings/evidence — mitigate with an explicit "ground every claim in the evidence
given; do not use outside knowledge" instruction, matching the existing signal/brief prompts'
proven pattern.

**Definition of done:** `POST /api/research/{ticker}` returns a valid `ResearchThesis` for a
real ticker, grounded in real Technical + News findings, with every finding traceable to
specific `Evidence` objects; all existing `/api/v1/*` routes still pass a smoke test; backend
restarts cleanly.

---

## Milestone 2 — Analytical Tools

**Goal:** Round out the tool layer using the verified-free evidence sources from
`target-state.md` §2, and add the two tools deferred from Milestone 1's minimal slice.

**New files:**
- `backend/intelligence/tools/fundamentals_tool.py` — revenue/earnings growth, margins,
  valuation ratios, historical trends from Alpha Vantage `OVERVIEW` (already fetched)
- `backend/intelligence/tools/sec_tool.py` — recent filings, filing-type classification, 8-K
  event flagging (data already fetched via `sec_edgar.py`; this is synthesis, not new fetching)
- `backend/intelligence/tools/earnings_tool.py` — EPS surprises + earnings calendar (new
  Finnhub endpoints, verified free) + insider transactions (new Finnhub endpoint, verified free,
  supersedes today's bare Form-4-link display)
- `backend/intelligence/tools/macro_tool.py` — FRED-backed CPI/unemployment/GDP/Fed-funds-rate
  evidence (key already configured)
- `backend/services/fred.py` — thin `httpx` wrapper matching the existing provider-module
  pattern (`finnhub.py`, `alpha_vantage.py`, etc.), raising `ProviderError` via the shared
  `wrap_httpx_error`

**Modified files:**
- `backend/intelligence/evidence_adapters.py` — adapters for the new evidence types
- `backend/intelligence/orchestrator.py` — always-run set grows to include the new tools

**Database migrations:** none.

**API changes:** none new — `/api/research/{ticker}` responses get richer as more tools run.

**Frontend changes:** none yet.

**Tests:** first real test coverage candidate — `fundamentals_tool`/`macro_tool` are pure
functions over fetched data, cheap to unit test without mocking HTTP (see Milestone 7 for when
this becomes systematic project-wide).

**Risks:** Alpha Vantage's 25 req/day cap is already the app's tightest constraint;
`fundamentals_tool` must reuse `aggregator.py`'s existing cached fundamentals rather than
issuing new Alpha Vantage calls.

**Definition of done:** all six tools (Technical, News, Fundamentals, SEC, Earnings, Macro)
independently callable and unit-testable; orchestrator runs all of them for a ticker request;
no increase in per-request Alpha Vantage calls.

---

## Milestone 3 — Research Orchestration

**Goal:** Move from "always run every tool" to real question-driven routing, and give the new
capability a frontend surface for the first time.

**New files:**
- `backend/intelligence/router_logic.py` (or fold into `orchestrator.py` if it stays small) —
  deterministic keyword/heuristic mapping from a free-text question to a tool subset (per the
  original request: avoid over-engineering a multi-agent framework; a simple rule table is the
  right tool until it demonstrably isn't)
- `frontend/components/Research.tsx` (or similar) — surfaces `ResearchThesis` in the existing
  visual language (violet = AI-generated, matching `AIBrief`/`TradeSignal`)

**Modified files:**
- `backend/routers/research.py` — add `POST /api/research/query`
- `frontend/lib/api.ts` — types + fetch wrapper for the new endpoint (candidate point to start
  splitting `lib/api.ts` into per-domain files, per the technical debt noted in
  `current-state.md` §5.9)
- `frontend/app/page.tsx` — wire in the new section

**Database migrations:** none.

**API changes:** `POST /api/research/query` (additive).

**Frontend changes:** new Research section; first UI consumer of the intelligence layer.

**Tests:** router_logic is a pure function (question string → tool list) — straightforward unit
tests for the routing table itself.

**Risks:** the biggest scope-creep risk in the whole roadmap — resist building a "smart" router
before there's evidence the deterministic one is insufficient.

**Definition of done:** a handful of representative questions ("Why did X fall this week?",
"What's the fundamental picture on X?") route to sensible tool subsets and produce a coherent
`ResearchThesis`; existing Brief/Ask/TradeSignal UI sections are unaffected.

---

## Milestone 4 — Signal Evaluation

**Goal:** Extend the *existing* `trade_signal` lifecycle (not replace it) with real forward-
return tracking and calibration, generalized so `ResearchThesis` can eventually feed the same
evaluator.

**New files:**
- `backend/intelligence/evaluators/signal_evaluator.py` — forward-return computation (1d/3d/5d/
  10d/20d), benchmark-relative return, MFE/MAE
- `backend/intelligence/evaluators/calibration.py` — confidence-bucketed accuracy (50-60,
  60-70, 70-80, 80-90, 90-100), Brier score
- `backend/routers/signals_performance.py` (or extend `routers/signal.py`) —
  `GET /api/signals/performance`, `GET /api/signals/calibration`

**Modified files:**
- `backend/db/database.py` — **migration**: `trade_signal` gains forward-return snapshot
  columns (`return_1d`, `return_3d`, `return_5d`, `return_10d`, `return_20d`,
  `benchmark_return`, `sector_return`, `mfe`, `mae`) or a new `signal_returns` child table keyed
  by `trade_signal.id` — decide based on whether returns are ever queried independent of the
  parent row (child table if so, to keep `trade_signal` from growing unboundedly wide)
- `backend/jobs/poller.py` — `resolve_pending_signals` also snapshots forward returns at each
  horizon, not just the final correct/incorrect outcome

**Database migrations:** yes — additive columns or a new table (see above). SQLite
`ALTER TABLE ... ADD COLUMN` via the existing `_migrate()` pattern in `database.py`, or a new
`CREATE TABLE IF NOT EXISTS signal_returns`.

**API changes:** `GET /api/signals/performance`, `GET /api/signals/calibration` (additive).

**Frontend changes:** new "Model Performance" section (per `target-state` UI sections list).

**Tests:** this milestone is the highest-value target for automated tests in the whole roadmap
— **look-ahead bias is a correctness property, not a style preference.** Test explicitly that:
resolving a signal never mutates its original `direction`/`confidence`/`price_at_signal`; a
signal's return calculation only ever uses prices dated *after* `generated_at`; re-running
resolution on an already-resolved signal is a no-op.

**Risks:** this is the most consequential milestone for platform credibility — a bug here
produces confidently wrong performance numbers. Budget real test-writing time, not just
implementation time.

**Definition of done:** every resolved signal has forward returns at all five horizons;
`/api/signals/calibration` shows real confidence-bucketed accuracy (even if the sample size is
still small); look-ahead-bias tests pass; historical `trade_signal` rows are backfilled or
explicitly left with null forward-return columns (not fabricated).

---

## Milestone 5 — Knowledge Graph Intelligence

**Goal:** Add provenance/confidence to graph edges, add a `graph_tool.py`, and add 2-hop /
portfolio-cross-exposure traversal.

**Modified files:**
- `backend/services/graph.py` — edge-creation functions (`link_subsidiary`, `link_contract`,
  `link_news_relationship`) gain `confidence` and `retrieved_at` parameters/properties
- `backend/services/graph_builder.py` — passes confidence through (SEC/USASpending-sourced
  edges: 1.0; Claude-inferred news edges: reuse the existing per-relationship evidence text,
  assign a lower default confidence, e.g. 0.6, until Milestone 4's calibration approach can be
  extended to graph inference too)
- `frontend/components/GraphView.tsx` — visually distinguish confirmed vs. inferred edges
  (e.g. solid vs. dashed already exists for style, extend the legend to explain confidence)

**New files:**
- `backend/intelligence/tools/graph_tool.py` — 1-hop (existing), 2-hop, supplier/customer
  concentration, government exposure, geographic exposure queries
- `backend/services/graph.py` additions: `get_2hop_exposure(symbol)`,
  `get_portfolio_exposure(symbols: list[str])`

**Database migrations:** ArcadeDB schema addition only (new edge properties), not SQLite.
Existing edges without `confidence`/`retrieved_at` need a one-time backfill script or a
"unknown confidence" default — decide explicitly, don't leave it implicit.

**API changes:** `graph_tool` becomes available to the orchestrator; existing
`GET /graph/{symbol}` response can optionally gain confidence fields (additive, doesn't break
existing consumers that ignore unknown fields).

**Frontend changes:** `GraphView.tsx` legend/styling update; no structural change.

**Tests:** confidence defaults and the confirmed-vs-inferred distinction are simple enough to
unit test without ArcadeDB running (test the Python logic that assigns confidence, not the graph
DB itself).

**Definition of done:** every new edge created after this milestone carries `confidence` +
`retrieved_at`; `GraphView.tsx` visibly distinguishes confirmed from inferred; a 2-hop query
(e.g. "who's 2 hops from a Taiwan-exposed supplier") returns correct results against a known
test graph.

---

## Milestone 6 — Portfolio Intelligence

**Goal:** Upgrade the portfolio from a position list into an intelligence object, using the
graph traversal from Milestone 5.

**New files:**
- `backend/intelligence/tools/portfolio_tool.py` — sector/industry/single-stock concentration
  (straightforward aggregation over existing `position` rows), graph-linked risk (calls
  `graph_tool`'s portfolio-exposure query), news/event exposure (cross-references portfolio
  symbols against recent findings from Milestone 2's tools)
- `frontend/components/PortfolioIntelligence.tsx` — the "32% Taiwan exposure" / "3 holdings
  share Microsoft as a customer" style callouts

**Modified files:**
- `backend/routers/portfolio.py` — add `GET /api/portfolio/exposure`,
  `GET /api/portfolio/intelligence` (additive; existing `GET /api/v1/portfolio` unchanged)

**Database migrations:** none — this is read-side aggregation over existing `position` +
graph data.

**API changes:** `GET /api/portfolio/exposure`, `GET /api/portfolio/intelligence`.

**Frontend changes:** new Portfolio Intelligence section alongside the existing `Portfolio.tsx`.

**Tests:** concentration math is pure and cheap to test; graph-linked risk needs a fixture
graph, same testing approach as Milestone 5.

**Risks:** prioritize genuinely useful callouts over exhaustive metrics — the original request
is explicit about this. Resist adding a metric just because the data is available.

**Definition of done:** portfolio view surfaces at least sector/single-stock concentration and
one graph-linked exposure callout, computed from real positions and real graph data, not
placeholder text.

---

## Milestone 7 — Production Hardening

**Goal:** Everything explicitly deferred as "not blocking earlier milestones" in
`target-state.md` §6, done properly once the platform shape has stabilized.

**Scope:**
- **Testing** (Phase 14): `pytest` + `pytest-asyncio` added as dev dependencies; provider
  mocking for timeout/rate-limit/malformed-data/empty-result cases; cache-expiry tests;
  duplicate-job-execution tests; the look-ahead-bias tests from Milestone 4 formalized into the
  suite rather than one-off scripts. Frontend: tests for critical state behavior where practical
  (e.g. the auto-refresh visibility-pause logic, the signal-history self-report gating).
- **Observability** (Phase 15): structured logging (request_id, ticker, tool name, provider,
  latency, cache hit/miss, model, token usage, estimated cost, success/failure); a reusable
  timing utility used by every tool and provider call.
- **Security** (Phase 16): request-size limits, ticker-format validation at the router boundary,
  basic rate limiting on the more expensive endpoints (research, signal generation), a documented
  production CORS/config story (the current hardcoded `localhost:3000` is correct for personal
  local use but should have a documented override path).
- **Provider abstraction** (Phase 19): `MarketDataProvider`/`NewsProvider` `Protocol`s, now that
  there's been real experience with multiple providers per category (Finnhub/Alpha Vantage,
  Finnhub/Marketaux) to design the interface against real usage rather than speculation.
- **Model abstraction** (Phase 20): `IntelligenceModel` wrapping `claude_analyst.py`'s Claude
  calls, if and when a second model provider is genuinely on the table — not before.

**Definition of done:** `pytest` passes in CI-equivalent local run covering the risk areas
listed above; structured logs answer "which provider fails most / which tool is slowest / what
did this query cost" from real log data; security checklist items are each either done or
explicitly documented as an accepted risk for a single-user local app.

---

## Sequencing notes

- Milestones 1-3 (evidence → tools → orchestration) are the architectural core and should ship
  in order — each depends on the previous one's abstractions existing.
- Milestone 4 (signal evaluation) can start any time after Milestone 1, since it extends the
  *existing* `trade_signal` table rather than depending on the new orchestrator. It's sequenced
  4th here because it's high-value and worth doing once the Evidence/Finding vocabulary exists
  to eventually unify signal evaluation with research-thesis evaluation, but it doesn't strictly
  block on Milestones 2-3 if there's a reason to prioritize it sooner.
- Milestones 5-6 (graph, portfolio) depend on each other in one direction only — 6 needs 5's
  traversal queries, not the reverse.
- Milestone 7 is deliberately last: testing/observability infrastructure is more valuable once
  there's a stable set of tools and endpoints to point it at, rather than being rebuilt every
  milestone as the shape changes.
