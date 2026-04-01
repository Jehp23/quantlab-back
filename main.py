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
    title=os.getenv("APP_NAME", "Quant Lab"),
    description="Robo Advisor + Quant Lab — API backend",
    version="0.1.0",
)

# CORS — permite que el frontend Next.js en localhost:3000 llame a esta API
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers montados
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
