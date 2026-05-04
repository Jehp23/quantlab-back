"""
Entry point del backend — FastAPI + CORS + routers.

Levanta en http://localhost:8000
Docs interactivas: http://localhost:8000/docs
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from routers import market, portfolio, asset, optimize, backtest, montecarlo, options, statistics

load_dotenv()

app = FastAPI(
    title=os.getenv("APP_NAME", "QuantLab — Analyst Platform"),
    description="API de research financiero: optimización, backtest, Monte Carlo, opciones BYMA.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(market.router)
app.include_router(portfolio.router)
app.include_router(asset.router)
app.include_router(optimize.router)
app.include_router(backtest.router)
app.include_router(montecarlo.router)
app.include_router(options.router)
app.include_router(statistics.router)


@app.get("/")
async def root():
    return {"status": "ok", "app": app.title, "docs": "/docs"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
