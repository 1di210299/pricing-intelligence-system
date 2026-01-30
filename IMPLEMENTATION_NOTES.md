"""
NOTAS DE IMPLEMENTACIÓN - Sistema de Inteligencia de Precios UPC
===================================================================

## Arquitectura del Sistema

### 1. Módulos Principales

#### UPC Validation (app/models/upc.py + app/services/upc_validator.py)
- Valida formato UPC-A (12 dígitos) y UPC-E (8 dígitos)
- Implementa validación de checksum según algoritmo estándar
- Limpia espacios y guiones automáticamente
- Proporciona método `is_valid()` para verificación sin excepciones

#### Market Pricing Ingestion (app/services/ebay_client.py)
- Integración con eBay Finding API
- Busca listings activos y completados/vendidos
- Extrae precios y calcula mediana/promedio
- Manejo robusto de errores con degradación graceful
- Soporta ambientes SANDBOX y PRODUCTION

#### Internal Data Processing (app/services/internal_data.py)
- Procesa CSV con datos internos de ventas
- Calcula estadísticas agregadas por categoría
- Lookup rápido por UPC
- Validación de columnas requeridas

#### Pricing Engine (app/services/pricing_engine.py)
- **Algoritmo de weighting dinámico:**
  * Base: 50% interno, 50% mercado
  * +20% interno si sell_through > 0.7
  * -15% interno si sell_through < 0.3
  * -15% interno si days_on_shelf > 60
  * +20% interno si market sample < 5
  * -10% interno si market sample > 20
  
- **Factores de decisión:**
  * Sell-through rate (umbral: 0.7)
  * Days on shelf (umbral: 60 días)
  * Market sample size (umbral: 5 muestras)
  * Price variance (umbral: 30% diferencia)
  
- **Confidence scoring:**
  * Base: 50
  * Ajustes según calidad de datos
  * Rango: 0-100

#### Cache Manager (app/cache/cache_manager.py)
- Soporta Redis o memoria in-memory
- TTL configurable (default: 1 hora)
- Serialización JSON automática
- Fallback graceful si Redis no disponible

### 2. API Endpoints

#### POST /price-recommendation
```json
Request:
{
  "upc": "012345678905",
  "internal_data": {  // opcional
    "internal_price": 29.99,
    "sell_through_rate": 0.75,
    "days_on_shelf": 45,
    "category": "Electronics"
  }
}

Response:
{
  "upc": "012345678905",
  "recommended_price": 28.50,
  "internal_vs_market_weighting": 0.65,
  "confidence_score": 85,
  "rationale": "High sell-through rate...",
  "market_data": {...},
  "internal_data": {...},
  "warnings": []
}
```

#### GET /health
Health check endpoint

#### GET /cache/stats
Estadísticas de cache (desarrollo)

#### DELETE /cache/clear
Limpiar cache (desarrollo)

### 3. Configuración

Variables de entorno (.env):
```
EBAY_APP_ID=your_app_id
EBAY_CERT_ID=your_cert_id
EBAY_DEV_ID=your_dev_id
EBAY_ENVIRONMENT=SANDBOX|PRODUCTION
USE_REDIS=true|false
REDIS_URL=redis://localhost:6379/0
CACHE_TTL=3600
LOG_LEVEL=INFO|DEBUG
```

### 4. Decisiones de Diseño

#### ¿Por qué usar mediana en vez de promedio?
- Más robusta ante outliers
- Mejor representa el "precio típico" del mercado

#### ¿Cómo manejar datos sparse?
- Sistema de weighting ajusta confianza según sample size
- Warnings explícitos para muestras pequeñas
- Degradación graceful: si no hay market data, usa solo internal

#### ¿Cómo validar UPC-E?
- Implementación simplificada
- En producción, se debería expandir UPC-E a UPC-A correctamente
- Actualmente valida checksum directamente sobre 8 dígitos

#### ¿Por qué cache?
- eBay API tiene rate limits
- Precios de mercado no cambian cada segundo
- TTL de 1 hora es balance razonable

### 5. Mejoras Futuras

1. **Algoritmo de Pricing:**
   - Machine learning para patrones estacionales
   - Análisis de competidores por categoría
   - Elasticidad de precio por producto
   - A/B testing de precios

2. **Integración eBay:**
   - Implementar OAuth 2.0 (actualmente usa App ID simple)
   - Paginar resultados para UPCs con muchos listings
   - Filtrar por condición del producto (nuevo/usado)
   - Considerar shipping costs

3. **Data Processing:**
   - Base de datos (PostgreSQL) en vez de CSV
   - Historial de precios (time series)
   - Análisis de tendencias
   - Dashboard de visualización

4. **Performance:**
   - Async/await para llamadas a eBay
   - Batch processing para múltiples UPCs
   - Worker queues para procesamiento pesado
   - Metrics y monitoring (Prometheus)

5. **Testing:**
   - Mocks para eBay API en tests
   - Integration tests end-to-end
   - Load testing
   - Coverage > 80%

6. **Security:**
   - Rate limiting por IP
   - API key authentication
   - Input sanitization
   - CORS configuración específica

### 6. Logging y Auditoría

Todas las decisiones de pricing se loguean en formato JSON:
```json
{
  "timestamp": "2026-01-28T10:30:00Z",
  "upc": "012345678905",
  "recommended_price": 28.50,
  "weighting": 0.65,
  "confidence": 85,
  "market_median": 27.99,
  "market_sample_size": 15,
  "internal_price": 29.99,
  "warnings": []
}
```

Esto permite:
- Auditoría de decisiones
- Análisis retrospectivo
- Detección de anomalías
- Mejora del algoritmo

### 7. Testing del Sistema

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Configurar .env (copiar de .env.example)

# 3. Ejecutar tests unitarios
pytest tests/ -v

# 4. Ejecutar API
uvicorn app.main:app --reload

# 5. Test manual (otra terminal)
python test_requests.py

# 6. Documentación interactiva
# Abrir http://localhost:8000/docs
```

### 8. Casos de Uso Cubiertos

✅ UPC válido con datos internos y de mercado
✅ UPC válido solo con datos internos
✅ UPC válido solo con datos de mercado
✅ UPC inválido (formato, checksum)
✅ Producto con alta rotación (sell-through > 0.7)
✅ Producto estancado (days_on_shelf > 60)
✅ Muestra de mercado pequeña (< 5)
✅ Diferencia de precio > 30%
✅ Cache de datos de mercado
✅ Logging de decisiones

### 9. Limitaciones Conocidas

1. **eBay API:**
   - Requiere credenciales válidas
   - Rate limits no implementados en cliente
   - Solo soporta Finding API (no Browse API)

2. **UPC-E:**
   - Validación simplificada
   - No expande correctamente a UPC-A

3. **Escalabilidad:**
   - Cache en memoria no escala horizontalmente
   - Sin soporte para procesamiento batch
   - Single-threaded (FastAPI default)

4. **Data Quality:**
   - No valida calidad de listings de eBay
   - No filtra por condición del producto
   - No considera costos de envío

### 10. Tiempo de Desarrollo

Estimación: 12-16 horas
- Setup y estructura: 1h
- UPC validation: 1h
- eBay client: 2-3h
- Internal data processing: 1h
- Pricing engine: 3-4h
- FastAPI integration: 2h
- Cache y logging: 1h
- Testing: 2-3h
- Documentación: 1h

Total real: ~14h
"""
