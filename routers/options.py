"""
Router de opciones — /options/*

Proxy hacia data912.com EOD analytics.
Los datos de opciones son del mercado argentino (BYMA) — tickers como GGAL, YPFD, PAMP.
Los Greeks (delta, gamma, theta, vega, rho) son calculados por data912.
"""

from fastapi import APIRouter, HTTPException

from services import data912_service
from models.schemas import OptionChainResponse, VolatilityData

router = APIRouter(prefix="/options", tags=["options"])


@router.get("/chain/{ticker}", response_model=OptionChainResponse)
async def get_option_chain(ticker: str):
    """
    Cadena de opciones completa de un activo del mercado argentino.

    Incluye strikes, vencimientos, precio de mercado y Greeks completos:
    delta (Δ), gamma (Γ), theta (Θ), vega (ν), rho (ρ), fair_value, ITM probability.
    Fuente: data912.com EOD.
    """
    try:
        return await data912_service.get_option_chain(ticker.upper())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/volatilities/{ticker}", response_model=VolatilityData)
async def get_volatilities(ticker: str):
    """
    Volatilidades implícita (IV) e histórica (HV) del activo.

    IV: volatilidad implícita en el precio de las opciones (forward-looking).
    HV: volatilidad histórica realizada (backward-looking).
    IV > HV → el mercado espera más volatilidad que la histórica (risk premium).
    IV < HV → el mercado está "barato" (raro).
    Fuente: data912.com EOD.
    """
    try:
        return await data912_service.get_volatilities(ticker.upper())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
