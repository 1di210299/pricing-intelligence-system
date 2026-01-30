# 🏷️ Sistema de Inteligencia de Precios basado en UPC

Sistema completo de recomendación de precios que combina datos del mercado (eBay) con datos internos de ventas para generar recomendaciones inteligentes.

## ✨ Características

- ✅ **Validación de UPC** (UPC-A 12 dígitos, UPC-E 8 dígitos con checksum)
- ✅ **Web Scraping de eBay** con sesión persistente (Playwright)
- ✅ **Procesamiento de datos internos** (3,602 registros de ventas)
- ✅ **Motor de recomendación inteligente** con múltiples factores
- ✅ **API REST con FastAPI** (documentación automática)
- ✅ **Caché** de datos de mercado (Redis o memoria)
- ✅ **Logging** completo para auditoría

## 🚀 Quick Start

```bash
# Setup automático
./quick_start.sh

# Prueba rápida (solo datos internos)
python test_integration.py --quick

# Prueba completa (con eBay)
python test_integration.py

# Iniciar API
./start.sh
```

## 📋 Requisitos

- Python 3.10+
- Playwright (para web scraping)
- Pandas (procesamiento de datos)
- FastAPI + Uvicorn (API)

## 📊 Datos

### Datos de Mercado (eBay)
- Web scraping de listings vendidos
- Estadísticas: median, average, min, max
- Sample size y confidence score
- Cache configurable

### Datos Internos (CSV)
```
Archivo: thrift_sales_12_weeks_with_subcategory.csv
Registros: 3,602 items
Período: 12 semanas
Columnas:
  - item_id, department, category, subcategory
  - brand, production_date, sold_date, days_to_sell
  - production_price, sold_price
```

**Departamentos:** Mens, Womens, Children  
**Marcas:** Nike, Adidas, Columbia, Levi's, Patagonia, Ralph Lauren, etc.

## 🏗️ Arquitectura

```
├── ebay_agent_4.py              # Web scraper de eBay (Playwright)
├── thrift_sales_*.csv           # Datos de ventas internos
├── app/
│   ├── main.py                  # API FastAPI
│   ├── config.py                # Configuración
│   ├── models/
│   │   ├── pricing.py           # Modelos Pydantic
│   │   └── upc.py               # Validación UPC
│   ├── services/
│   │   ├── ebay_client.py       # Cliente eBay
│   │   ├── internal_data.py     # Procesador CSV
│   │   ├── pricing_engine.py    # Motor de recomendación
│   │   └── upc_validator.py     # Validador UPC
│   ├── cache/
│   │   └── cache_manager.py     # Gestión de caché
│   └── utils/
│       └── logger.py            # Logging
└── tests/                       # Tests unitarios
```

## 🎯 Algoritmo de Pricing

El motor considera:

1. **Sell-through rate** (> 0.7 = precio funciona bien)
2. **Days on shelf** (> 60 días = considerar reducir)
3. **Market sample size** (< 5 = baja confianza)
4. **Price variance** (> 30% = posible outlier)
5. **Category margins** (diferentes por tipo)

### Ejemplo de Decisión

```python
Input:
  - Search: "Nike Sneakers"
  - Internal: $45.00, sell-through 85%, 25 días
  - Market: median $52.00, 15 samples

Output:
  - Recommended: $48.50
  - Weighting: 0.65 (65% interno, 35% mercado)
  - Confidence: 85/100
  - Rationale: "High sell-through rate (0.85). Internal price performing well..."
```

## 📡 API Endpoints

### POST `/price-recommendation`
Obtener recomendación de precio

**Request:**
```json
{
  "upc": "Nike Air Max 90",
  "internal_data": null
}
```

**Response:**
```json
{
  "upc": "Nike Air Max 90",
  "recommended_price": 48.50,
  "internal_vs_market_weighting": 0.65,
  "confidence_score": 85,
  "rationale": "High sell-through rate...",
  "market_data": {
    "median_price": 52.00,
    "average_price": 51.20,
    "sample_size": 15,
    "low_confidence": false
  },
  "internal_data": {
    "internal_price": 45.00,
    "sell_through_rate": 0.85,
    "days_on_shelf": 25,
    "category": "Shoes"
  },
  "warnings": []
}
```

### GET `/health`
Health check

### GET `/docs`
Documentación interactiva (Swagger UI)

## 🧪 Testing

```bash
# Tests unitarios
pytest tests/

# Test de integración (quick)
python test_integration.py --quick

# Test de integración (completo)
python test_integration.py
```

## 🔧 Configuración

### Variables de Entorno (.env)
```bash
# API
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO

# eBay (opcional para API oficial)
EBAY_APP_ID=your_app_id
EBAY_ENVIRONMENT=SANDBOX

# Cache
CACHE_TYPE=memory  # o 'redis'
CACHE_TTL=3600
REDIS_HOST=localhost
REDIS_PORT=6379
```

## ⚠️ Notas Importantes

### Web Scraping
- ⏱️ Delays aleatorios para evitar bloqueos
- 🔒 Sesión persistente del navegador
- ⚠️ Respetar términos de servicio de eBay
- 🚫 No hacer abuse del scraping

### Rendimiento
- 💾 Cache de market data (default 1 hora)
- 🚀 Sesión persistente reduce overhead
- 📊 Datos internos pre-cargados en memoria

### Limitaciones
- Sin UPCs directos en CSV → búsqueda por keywords
- Web scraping puede ser bloqueado
- Sample size variable por producto

## 📈 Próximos Pasos

- [ ] Dashboard de visualización
- [ ] Más fuentes de market data
- [ ] Machine Learning para predicciones
- [ ] Sistema de alertas
- [ ] A/B testing de algoritmos

## 📚 Documentación

- `INTEGRATION_GUIDE.md` - Guía detallada de integración
- `IMPLEMENTATION_NOTES.md` - Notas de implementación
- `/docs` - API documentation (cuando servidor esté corriendo)

## 🤝 Contribuir

Este es un proyecto de desafío técnico. Ver `IMPLEMENTATION_NOTES.md` para detalles técnicos.

## 📝 License

MIT

---

**Tiempo de desarrollo:** 12-16 horas  
**Stack:** Python 3.10, FastAPI, Pandas, Playwright, Pydantic  
**Última actualización:** Enero 2026
