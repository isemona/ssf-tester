from fastapi import FastAPI

from app.db import init_db, list_events
from app.receiver.router import router as receiver_router
from app.transmitter.router import router as transmitter_router
from app.transmitter.router import wellknown_router

app = FastAPI(title="SSF Tester")


@app.on_event("startup")
def on_startup():
    init_db()


app.include_router(wellknown_router)
app.include_router(transmitter_router)
app.include_router(receiver_router)


@app.get("/events")
def get_events(limit: int = 50):
    return list_events(limit=limit)


@app.get("/")
def root():
    return {"status": "ok", "docs": "/docs"}
