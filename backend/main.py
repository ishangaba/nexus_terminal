from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import apply_settings_overrides
from db.database import init_db
from jobs.poller import start_scheduler
from routers import ask, graph, portfolio, research, settings, signal, signals_performance, ticker, watchlist

app = FastAPI(title="Nexus Terminal API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    # Also allow the frontend when it's opened from another device on the same private network
    # (e.g. http://192.168.1.42:3000). Scoped to RFC 1918 private ranges + localhost on port
    # 3000 specifically — not a public wildcard — since this is a personal LAN convenience, not
    # a hardening story for exposing the app to the open internet.
    allow_origin_regex=(
        r"http://(localhost|127\.0\.0\.1"
        r"|10(?:\.\d{1,3}){3}"
        r"|172\.(?:1[6-9]|2\d|3[0-1])(?:\.\d{1,3}){2}"
        r"|192\.168(?:\.\d{1,3}){2}"
        r"):3000"
    ),
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
app.include_router(ticker.router)
app.include_router(watchlist.router)
app.include_router(ask.router)
app.include_router(graph.router)
app.include_router(settings.router)
app.include_router(portfolio.router)
app.include_router(signal.router)
app.include_router(research.router)
app.include_router(signals_performance.router)


@app.on_event("startup")
def on_startup():
    init_db()
    apply_settings_overrides()
    start_scheduler()


@app.get("/health")
def health():
    return {"status": "ok"}
