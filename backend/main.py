from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db.database import init_db
from jobs.poller import start_scheduler
from routers import ask, ticker, watchlist

app = FastAPI(title="Nexus Terminal API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)
app.include_router(ticker.router)
app.include_router(watchlist.router)
app.include_router(ask.router)


@app.on_event("startup")
def on_startup():
    init_db()
    start_scheduler()


@app.get("/health")
def health():
    return {"status": "ok"}
