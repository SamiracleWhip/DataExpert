from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).parent.parent / ".env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import districts, buildings, trends, stats, contracts, stations, chat

app = FastAPI(title="Singapore Rentals API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(districts.router)
app.include_router(buildings.router)
app.include_router(trends.router)
app.include_router(stats.router)
app.include_router(contracts.router)
app.include_router(stations.router)
app.include_router(chat.router)


@app.get("/")
async def root():
    return {"status": "ok", "docs": "/docs"}
