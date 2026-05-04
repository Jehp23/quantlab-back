# QuantLab · Backend API

API de research financiero cuantitativo construida con FastAPI. Provee datos de mercado, optimización de portafolios, backtesting, Monte Carlo y opciones del mercado argentino.

**Frontend:** [quantlab2.vercel.app](https://quantlab2.vercel.app) · **Repo frontend:** [quantlab-front](https://github.com/Jehp23/quantlab-front)

---

## Endpoints

| Router | Prefijo | Descripción |
|--------|---------|-------------|
| `market` | `/market` | Cotizaciones y datos históricos — global (yfinance) y argentino (data912) |
| `portfolio` | `/portfolio` | Métricas de portafolio: retorno, volatilidad, Sharpe, drawdown |
| `optimize` | `/optimize` | Frontera eficiente: máximo Sharpe, mínima varianza, risk parity |
| `backtest` | `/backtest` | Backtesting con rebalanceo periódico vs SPY benchmark |
| `montecarlo` | `/montecarlo` | Simulación Monte Carlo de portafolios |
| `options` | `/options` | Cadena de opciones BYMA con Greeks — vía data912 |
| `statistics` | `/statistics` | Análisis estadístico completo: VaR, CVaR, normalidad, ACF, T-test |
| `asset` | `/asset` | Datos y métricas de activos individuales |

Docs interactivas en `/docs` (Swagger UI).

---

## Stack

- **FastAPI** + **Uvicorn**
- **yfinance** — datos globales (NYSE, NASDAQ, ETFs)
- **data912.com** — mercado argentino (BYMA, CEDEARs, opciones)
- **PyPortfolioOpt** — optimización media-varianza
- **NumPy / Pandas / SciPy** — cálculos cuantitativos

---

## Setup local

```bash
git clone https://github.com/Jehp23/quantlab-back
cd quantlab-back
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

API disponible en `http://localhost:8000` · Swagger en `http://localhost:8000/docs`.

---

## Deploy (Render)

- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
- **Runtime:** Python 3.11.9 (definido en `runtime.txt`)

No requiere variables de entorno obligatorias. Todas las fuentes de datos (yfinance, data912) son públicas.
