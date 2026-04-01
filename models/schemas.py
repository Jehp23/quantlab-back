"""
Schemas Pydantic v2 — modelos de request y response para la API.

Los tipos del frontend TypeScript deben ser espejo de estos schemas.
"""

from pydantic import BaseModel, Field
from typing import Optional

from constants.rates import RISK_FREE_RATE


# ── Market ────────────────────────────────────────────────────────────────────

class QuoteResponse(BaseModel):
    ticker: str
    name: str
    price: float
    currency: str
    change: float          # cambio absoluto en el día
    change_pct: float      # cambio porcentual en el día
    volume: Optional[int] = None
    market_cap: Optional[float] = None
    fifty_two_week_high: Optional[float] = None
    fifty_two_week_low: Optional[float] = None
    beta: Optional[float] = None
    dividend_yield: Optional[float] = None


class OHLCPoint(BaseModel):
    date: str              # ISO 8601: "2024-01-15"
    open: float
    high: float
    low: float
    close: float
    volume: Optional[int] = None


class HistoricalResponse(BaseModel):
    ticker: str
    period: str
    data: list[OHLCPoint]


class ARStockItem(BaseModel):
    symbol: str
    price: float           # c — precio actual
    change_pct: float      # pct_change
    bid: Optional[float] = None    # px_bid
    ask: Optional[float] = None    # px_ask
    volume: Optional[int] = None   # v


class ARStocksResponse(BaseModel):
    data: list[ARStockItem]
    count: int


class ARCedearsResponse(BaseModel):
    data: list[ARStockItem]
    count: int


# ── Portfolio ─────────────────────────────────────────────────────────────────

class PortfolioAnalyzeRequest(BaseModel):
    tickers: list[str] = Field(..., min_length=1)
    weights: list[float] = Field(..., min_length=1)
    period: str = "2y"


class PortfolioMetrics(BaseModel):
    annual_return: float       # retorno anualizado
    sigma: float               # volatilidad anualizada
    sharpe: float              # Sharpe Ratio (Rf=BIL)
    sortino: float             # Sortino Ratio
    calmar: float              # Calmar Ratio
    max_drawdown: float        # máximo drawdown (negativo)
    var_95: float              # VaR paramétrico al 95%
    correlation: dict[str, dict[str, float]]  # matriz correlación


class PortfolioAnalyzeResponse(BaseModel):
    tickers: list[str]
    weights: list[float]
    period: str
    metrics: PortfolioMetrics


class PortfolioBuildRequest(BaseModel):
    risk_score: int = Field(..., ge=0, le=100)
    investment_goal: str | None = None
    horizon_years: int | None = Field(default=None, ge=0, le=50)
    liquidity_need: str | None = None
    experience_level: str | None = None
    monthly_contribution: float | None = Field(default=None, ge=0)
    emergency_buffer_months: int | None = Field(default=None, ge=0, le=60)


class PortfolioBuildResponse(BaseModel):
    profile_name: str
    description: str
    allocation: dict[str, float]   # asset_class -> %
    etf_weights: dict[str, float]  # ticker -> peso
    investor_context: dict[str, str | int | float | None]
    suitability: list[str]
    rationale: list[str]
    rebalance_policy: str
    next_steps: list[str]


class EquityCurvePoint(BaseModel):
    date: str              # "2024-01-15"
    portfolio_value: float # valor del portafolio (base 100)
    benchmark_value: float # valor del benchmark SPY (base 100)


class EquityCurveResponse(BaseModel):
    tickers: list[str]
    weights: list[float]
    period: str
    initial_value: float = 100.0
    data: list[EquityCurvePoint]


# ── Asset Analysis ────────────────────────────────────────────────────────────

class RollingVolPoint(BaseModel):
    date: str
    volatility: float


class AssetMetrics(BaseModel):
    annual_return: float
    sigma: float
    sharpe: float
    sortino: float
    calmar: float
    max_drawdown: float
    var_95: float
    beta: Optional[float] = None    # vs benchmark
    alpha: Optional[float] = None   # Jensen alpha vs benchmark


class AssetAnalysisResponse(BaseModel):
    ticker: str
    benchmark: str
    period: str
    quote: QuoteResponse
    ohlc: list[OHLCPoint]
    metrics: AssetMetrics
    rolling_vol: list[RollingVolPoint]


class CompareSeriesPoint(BaseModel):
    date: str
    values: dict[str, float]   # ticker -> precio normalizado (base 100)


class CompareTicker(BaseModel):
    ticker: str
    metrics: AssetMetrics


class AssetCompareResponse(BaseModel):
    tickers: list[str]
    period: str
    series: list[CompareSeriesPoint]
    metrics: list[CompareTicker]


# ── Optimize ──────────────────────────────────────────────────────────────────

class OptimizeRequest(BaseModel):
    tickers: list[str] = Field(..., min_length=2)
    period: str = "5y"
    risk_free_rate: float = RISK_FREE_RATE


class OptimizeResponse(BaseModel):
    method: str
    weights: dict[str, float]
    expected_return: float
    expected_volatility: float
    sharpe: float


# ── Backtest ──────────────────────────────────────────────────────────────────

class BacktestRequest(BaseModel):
    tickers: list[str]
    weights: list[float]
    start: str     # "2020-01-01"
    end: str       # "2024-12-31"
    rebalance_freq: str = "monthly"   # monthly | quarterly | annually


class BacktestDataPoint(BaseModel):
    date: str
    value: float
    benchmark_value: Optional[float] = None


class BacktestResponse(BaseModel):
    data: list[BacktestDataPoint]
    metrics: PortfolioMetrics


# ── Monte Carlo ───────────────────────────────────────────────────────────────

class MonteCarloRequest(BaseModel):
    tickers: list[str]
    weights: list[float]
    horizon_days: int = 252
    simulations: int = 1000
    initial_value: float = 10000.0
    seed: Optional[int] = None  # None = aleatoriedad real; int = reproducibilidad


class MonteCarloResponse(BaseModel):
    percentile_5: list[float]
    percentile_50: list[float]
    percentile_95: list[float]
    final_values: list[float]   # distribución de valores finales


# ── Options ───────────────────────────────────────────────────────────────────

class OptionContract(BaseModel):
    symbol: str
    underlying: str
    expiry: str
    strike: float
    option_type: str      # "call" | "put"
    price: float
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None
    rho: Optional[float] = None
    iv: Optional[float] = None
    itm_prob: Optional[float] = None
    fair_value: Optional[float] = None


class OptionChainResponse(BaseModel):
    ticker: str
    calls: list[OptionContract]
    puts: list[OptionContract]


class VolatilityData(BaseModel):
    ticker: str
    iv_short: Optional[float] = None
    iv_medium: Optional[float] = None
    iv_long: Optional[float] = None
    hv_short: Optional[float] = None
    hv_medium: Optional[float] = None
    hv_long: Optional[float] = None
    iv_hv_ratio: Optional[float] = None
    iv_percentile: Optional[float] = None
