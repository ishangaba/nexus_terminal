# Nexus Terminal — Target State

Companion to `current-state.md`. Describes the architecture Nexus Terminal is evolving toward:
an evidence-grounded AI financial intelligence platform, built incrementally on top of what
already exists (see `current-state.md` §4 for what's explicitly preserved).

## 1. Core principle

```text
Raw Financial Sources
        ↓
Data Acquisition Layer        (existing services/*.py providers)
        ↓
Normalized Evidence Layer     (NEW — intelligence/models/evidence.py + adapters)
        ↓
Specialized Analytical Tools  (NEW — intelligence/tools/*.py, deterministic-first)
        ↓
Evidence + Confidence + Provenance
        ↓
Research Orchestrator         (NEW — intelligence/orchestrator.py)
        ↓
Final Intelligence / Thesis   (NEW — intelligence/models/thesis.py)
        ↓
Signal Evaluation + Historical Feedback   (EXTENDS existing trade_signal lifecycle)
```

The LLM is never the source of financial facts. It reasons over evidence gathered by
deterministic tools and external providers, and every major conclusion should be traceable to
source, timestamp, ticker, evidence type, raw/normalized value, confidence, and interpretation.

**This is additive, not a rewrite.** The existing `/api/v1/*` routes, the `TradeSignal`
lifecycle, the graph, and the frontend keep working unchanged throughout. New capability lands
under a new `intelligence/` package and new `/api/research/*` / `/api/signals/*` routes; old and
new coexist until a later milestone decides whether/how to migrate call sites.

## 2. Evidence types and their sources

| Evidence type | Source | Status |
|---|---|---|
| `PRICE`, `VOLUME` | Finnhub | Existing data, needs an Evidence adapter |
| `TECHNICAL_INDICATOR` | Computed server-side from Alpha Vantage OHLCV (Python port of the existing `frontend/lib/indicators.ts` math) | New Python module, ported logic |
| `FUNDAMENTAL` | Alpha Vantage `OVERVIEW` | Existing data, needs an Evidence adapter |
| `SEC_FILING` | SEC EDGAR | Existing data, needs an Evidence adapter |
| `NEWS` | Finnhub + Marketaux | Existing data, needs an Evidence adapter |
| `SENTIMENT` | Claude-scored per headline (existing `score_sentiment`) | Existing data, needs an Evidence adapter |
| `GOVERNMENT_CONTRACT` | USASpending.gov | Existing (graph-only today), needs an Evidence adapter |
| `EARNINGS` | Finnhub `/stock/earnings` (EPS actual/estimate/surprise) + `/calendar/earnings` | **New — verified free, zero new signup** |
| `INSIDER_TRANSACTION` | Finnhub `/stock/insider-transactions` (structured Form 4 data) | **New — verified free, zero new signup**; supersedes showing Form 4 as a bare filing link |
| `ANALYST_ESTIMATE` | Finnhub `/stock/recommendation` (buy/hold/sell trend) | **New — verified free.** Price targets specifically are Finnhub-paid-gated (`403` confirmed live); not pursued for now — recommendation trends cover most of the value |
| `MACRO_EVENT` | FRED (Federal Reserve Economic Data) — CPI, unemployment, GDP, Fed funds rate | **New — key configured and verified live** |
| `SUPPLY_CHAIN_RELATIONSHIP`, `COMPETITOR_RELATIONSHIP` | Claude-inferred from news (existing `SUPPLIES_TO`/`COMPETES_WITH`/`PARTNERS_WITH` graph edges) | Existing, stays as the source — no free institutional-quality provider exists for this category |
| `INSTITUTIONAL_HOLDING` | — | **Deferred / logged gap.** Finnhub's 13F/institutional-ownership/fund-ownership endpoints are all paid-gated (`403` confirmed live); no working free alternative found after direct verification. Revisit only if a specific provider is vetted with a real key, or if a DIY SEC-13F reverse-index is judged worth the engineering cost |

## 3. New backend module: `backend/intelligence/`

```text
backend/
    intelligence/
        __init__.py
        orchestrator.py            # deterministic tool routing — NOT a multi-agent framework

        models/
            evidence.py             # Evidence, EvidenceType
            findings.py             # AnalyticalFinding
            thesis.py                # ResearchThesis

        evidence_adapters.py        # aggregator.gather_context() dict output -> list[Evidence]

        tools/
            technical_tool.py       # deterministic: SMA/RSI/MACD/Bollinger/trend, no LLM call
            news_tool.py             # deterministic: dedup/cluster/recency-weight + existing sentiment scores, no new LLM call
            fundamentals_tool.py     # (Milestone 2)
            sec_tool.py              # (Milestone 2)
            graph_tool.py            # (Milestone 5)
            earnings_tool.py         # (Milestone 2 — Finnhub earnings/insider/recommendation)
            macro_tool.py            # (Milestone 2 — FRED)
            portfolio_tool.py        # (Milestone 6)

        evaluators/                 # (Milestone 4)
            signal_evaluator.py
            calibration.py
            backtester.py
```

Per the existing engineering rules: routers stay thin, business logic lives in
`intelligence/`/`services/`, every boundary is a Pydantic model, tools are deterministic where
possible and only call Claude for genuine semantic work (classification, entity/relationship
extraction, cross-source synthesis, explanation, conflict resolution).

### 3.1 Evidence model

```python
class EvidenceType(str, Enum):
    PRICE = "PRICE"
    VOLUME = "VOLUME"
    TECHNICAL_INDICATOR = "TECHNICAL_INDICATOR"
    FUNDAMENTAL = "FUNDAMENTAL"
    EARNINGS = "EARNINGS"
    SEC_FILING = "SEC_FILING"
    NEWS = "NEWS"
    SENTIMENT = "SENTIMENT"
    GOVERNMENT_CONTRACT = "GOVERNMENT_CONTRACT"
    INSIDER_TRANSACTION = "INSIDER_TRANSACTION"
    ANALYST_ESTIMATE = "ANALYST_ESTIMATE"
    MACRO_EVENT = "MACRO_EVENT"
    SUPPLY_CHAIN_RELATIONSHIP = "SUPPLY_CHAIN_RELATIONSHIP"
    COMPETITOR_RELATIONSHIP = "COMPETITOR_RELATIONSHIP"
    # INSTITUTIONAL_HOLDING intentionally omitted — no source wired yet (§2)

class Evidence(BaseModel):
    id: str
    ticker: str
    evidence_type: EvidenceType
    source: str                    # e.g. "finnhub", "alpha_vantage", "sec_edgar", "fred"
    source_url: str | None = None
    observed_at: datetime          # when the underlying fact occurred/was published (UTC)
    retrieved_at: datetime         # when Nexus fetched it (UTC)
    value: Any
    normalized_value: Any | None = None
    confidence: float              # 1.0 for directly-observed provider data; lower for inferred
    metadata: dict = {}
```

Confidence convention for Milestone 1: directly-observed provider values (price, fundamentals,
filings) get `1.0`; Claude-scored sentiment gets `0.7` (reflects NLP-derived uncertainty, not a
calibrated number yet — calibration is Milestone 4). This is a starting convention, not a
finished calibration system.

### 3.2 Findings and Thesis

`AnalyticalFinding` (one per tool call) and `ResearchThesis` (the synthesized output) follow the
shapes specified in the original request — `ResearchThesis` generalizes what `TradeSignal`
already does (direction/confidence/reasoning/risks) into a reusable platform object that can
back the analyst brief, the trade signal, portfolio intelligence, and research history. The
existing `TradeSignal` Pydantic model and `SIGNAL_SYSTEM_PROMPT` are **not** replaced in
Milestone 1 — `ResearchThesis` lands alongside them via the new `/api/research/*` surface.
Whether/how `TradeSignal` eventually becomes a specialized view over `ResearchThesis` is a
Milestone 3+ decision, made after the orchestrator has more than two tools to route between.

## 4. Research Orchestrator

Milestone 1 ships the simplest version that works: `POST /api/research/{ticker}` always runs
every available tool (today: Technical + News) for that ticker, no question-based routing. This
matches the instruction to implement a deterministic/router-based strategy first rather than
building a routing system before there's more than one meaningful routing decision to make.

Question-driven routing (`POST /api/research/query`, e.g. mapping "Why did NVDA fall this week?"
to Market+Technical+News+SEC+Graph, or "What risks does Taiwan create for my portfolio?" to
Portfolio+Graph+News+SEC+Macro) is explicitly **Milestone 3**, once `fundamentals_tool`,
`sec_tool`, `earnings_tool`, and `macro_tool` exist to route between. Building the router before
the tools it routes to would be routing logic with nothing to test it against.

## 5. API surface

New, additive routes (existing `/api/v1/*` routes are untouched):

```text
POST /api/research/{ticker}       # Milestone 1 — always-run-available-tools
POST /api/research/query          # Milestone 3 — question-driven tool selection
GET  /api/signals/performance     # Milestone 4
GET  /api/signals/calibration     # Milestone 4
```

No route is removed or renamed in any milestone covered by this roadmap. If `TradeSignal`
generation is ever migrated onto the orchestrator, it happens via the existing
`/api/v1/ticker/{symbol}/signal` route staying in place and changing its *implementation*, not
its contract — the frontend never has to change to keep working.

## 6. Explicit non-goals for the current roadmap

- **No multi-agent framework.** The orchestrator is a deterministic function, not a fleet of
  autonomous LLM agents. Tools are Python/deterministic wherever possible; Claude is used only
  where semantic reasoning is genuinely the bottleneck.
- **No new database engine or ORM.** Evidence/Findings/Thesis are constructed in-memory per
  request in Milestone 1. Persisting research history (Phase 12 in the original spec) is a
  later milestone, made after real usage shows what actually needs to survive a request.
- **No provider or model abstraction layer yet** (`MarketDataProvider` Protocol,
  `IntelligenceModel` abstraction). Both are legitimate target-architecture ideas but are
  premature with a single implementation of each — they're listed in the roadmap as Milestone 7
  hardening work, not blocking earlier milestones.
- **No institutional-holdings integration** until a real free or vetted-paid source exists (§2).

See `roadmap.md` for the milestone breakdown, files touched per milestone, and definition of
done for each.
