from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import apply_settings_overrides
from db.database import init_db
from jobs.poller import start_scheduler
from routers import ask, graph, settings, ticker, watchlist

app = FastAPI(title="Nexus Terminal API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
app.include_router(ticker.router)
app.include_router(watchlist.router)
app.include_router(ask.router)
app.include_router(graph.router)
app.include_router(settings.router)


@app.on_event("startup")
def on_startup():
    init_db()
    apply_settings_overrides()
    start_scheduler()


@app.get("/health")
def health():
    return {"status": "ok"}
