# Sistema de Inteligencia de Precios basado en UPC

Sistema que combina datos de mercado (eBay) con datos internos de ventas para recomendar precios óptimos.

## Stack Tecnológico
- Python 3.10+
- FastAPI
- Pydantic
- Redis (opcional, para cache)
- Pandas (procesamiento de datos)

## Instalación

```bash
# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En macOS/Linux

# Instalar dependencias
pip install -r requirements.txt
```

## Configuración

Crear archivo `.env` en la raíz del proyecto:

```env
EBAY_APP_ID=your_app_id_here
EBAY_CERT_ID=your_cert_id_here
EBAY_DEV_ID=your_dev_id_here
EBAY_ENVIRONMENT=PRODUCTION  # o SANDBOX
REDIS_URL=redis://localhost:6379/0  # opcional
CACHE_TTL=3600  # segundos
```

## Ejecución

```bash
# Iniciar servidor
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

### POST /price-recommendation
Obtiene recomendación de precio para un UPC.

**Request:**
```json
{
  "upc": "012345678905",
  "internal_data": {
    "internal_price": 29.99,
    "sell_through_rate": 0.75,
    "days_on_shelf": 45,
    "category": "Electronics"
  }
}
```

**Response:**
```json
{
  "upc": "012345678905",
  "recommended_price": 28.50,
  "internal_vs_market_weighting": 0.65,
  "confidence_score": 85,
  "rationale": "High sell-through rate (0.75) indicates internal price is effective. Market median (27.99) is slightly lower. Recommendation balances both sources with 65% weight on internal data.",
  "market_data": {
    "median_price": 27.99,
    "average_price": 28.45,
    "sample_size": 15,
    "timestamp": "2026-01-28T10:30:00Z"
  },
  "internal_data": {
    "internal_price": 29.99,
    "sell_through_rate": 0.75,
    "days_on_shelf": 45,
    "category": "Electronics"
  }
}
```

### GET /health
Verifica el estado del servicio.

## Estructura del Proyecto

```
coding_challenge/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app
│   ├── config.py               # Configuración
│   ├── models/
│   │   ├── __init__.py
│   │   ├── pricing.py          # Modelos Pydantic
│   │   └── upc.py              # Validación UPC
│   ├── services/
│   │   ├── __init__.py
│   │   ├── upc_validator.py    # Validación de UPC
│   │   ├── ebay_client.py      # Cliente eBay API
│   │   ├── internal_data.py    # Procesamiento datos internos
│   │   └── pricing_engine.py   # Motor de recomendación
│   ├── cache/
│   │   ├── __init__.py
│   │   └── cache_manager.py    # Gestión de cache
│   └── utils/
│       ├── __init__.py
│       └── logger.py           # Logging
├── data/
│   └── sample_internal_data.csv
├── tests/
│   ├── __init__.py
│   ├── test_upc_validator.py
│   ├── test_pricing_engine.py
│   └── test_api.py
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## Algoritmo de Recomendación

El motor de precios considera:

1. **Sell-through rate**: Si > 0.7, mayor peso a precio interno
2. **Days on shelf**: Si > 60 días, considera reducción de precio
3. **Market sample size**: Si < 5, baja confianza en datos de mercado
4. **Price variance**: Si diferencia > 30% entre interno y mercado, señal de alerta
5. **Categoría**: Ajustes específicos por categoría

## Testing

```bash
pytest tests/
```
