"""
Entry point del backend — FastAPI + CORS + routers.

Levanta en http://localhost:8000
Docs interactivas: http://localhost:8000/docs
"""

import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from db import init_db
from routers import auth, workspace, market, portfolio, asset, optimize, backtest, montecarlo, options, statistics

load_dotenv()
init_db()

app = FastAPI(
    title=os.getenv("APP_NAME", "PonchoCapital Analyst Platform"),
    description="Internal API para research financiero, optimization y portfolio workflows.",
    version="0.1.0",
)

# CORS — abierto para proyecto educativo open source
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers montados
app.include_router(auth.router)
app.include_router(workspace.router)
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
