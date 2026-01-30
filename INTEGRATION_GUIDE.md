# Sistema de Inteligencia de Precios - Configuración Actualizada

## Datos Proporcionados Integrados

Se han integrado exitosamente los siguientes archivos:

1. **ebay_agent_4.py** - Agente de web scraping de eBay con sesión persistente usando Playwright
2. **thrift_sales_12_weeks_with_subcategory.csv** - Datos de ventas con 3,602 registros
3. **README (3).md** - Documentación del agente eBay

## Cambios Realizados

### 1. Cliente eBay (`app/services/ebay_client.py`)
- ✅ Reemplazado por implementación con web scraping usando `ebay_agent_4`
- ✅ Sesión persistente del navegador para evitar bloqueos
- ✅ Soporte asíncrono con `async/await`
- ✅ Retorna datos de listings vendidos con estadísticas (median, avg, min, max)

### 2. Procesador de Datos Internos (`app/services/internal_data.py`)
- ✅ Adaptado al nuevo formato CSV con columnas:
  - `item_id`, `department`, `category`, `subcategory`
  - `brand`, `production_date`, `sold_date`, `days_to_sell`
  - `production_price`, `sold_price`
- ✅ Búsqueda por keywords (brand, category, subcategory)
- ✅ Cálculo automático de sell-through rate
- ✅ Métricas agregadas por categoría

### 3. API Principal (`app/main.py`)
- ✅ Sesión persistente de eBay en startup/shutdown
- ✅ Búsqueda por keywords en lugar de UPC directo
- ✅ Soporte asíncrono completo

### 4. Dependencias (`requirements.txt`)
- ✅ Agregado `playwright==1.40.0` para web scraping

## Estructura de Datos

### CSV de Ventas Internas
```csv
item_id,department,category,subcategory,brand,production_date,sold_date,days_to_sell,production_price,sold_price
1,Children,Shoes,Sneakers,Old Navy,2025-11-10,2025-12-23,43.0,6.84,4.63
2,Children,Bottoms,Jeans,Adidas,2025-11-09,2025-11-17,8.0,17.08,18.08
...
```

**Estadísticas:**
- Total registros: 3,602
- Items vendidos: ~2,700 (75% sell-through rate estimado)
- Departamentos: Mens, Womens, Children
- Marcas: Nike, Adidas, Columbia, Levi's, Patagonia, etc.

## Instalación y Configuración

### 1. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 2. Instalar navegadores de Playwright
```bash
playwright install chromium
```

### 3. Configurar variables de entorno (opcional)
```bash
cp .env.example .env
# Editar .env si es necesario
```

## Pruebas

### Prueba Rápida (Solo Datos Internos)
```bash
python test_integration.py --quick
```

### Prueba Completa (Con Scraping de eBay)
```bash
python test_integration.py
```
**⚠️ Advertencia:** Abrirá un navegador y hará scraping real de eBay.

### Ejecutar API
```bash
python -m app.main
# o
./start.sh
```

## Ejemplos de Uso

### 1. Prueba desde Python
```python
import asyncio
from app.services.ebay_client import eBayClient
from app.services.internal_data import InternalDataProcessor
from app.services.pricing_engine import PricingEngine

async def main():
    # Inicializar servicios
    ebay = eBayClient(headless=True)
    await ebay.start_session()
    
    internal = InternalDataProcessor("thrift_sales_12_weeks_with_subcategory.csv")
    engine = PricingEngine()
    
    # Buscar datos
    search_term = "Nike Sneakers"
    internal_data = internal.search_by_keywords(search_term)
    market_data = await ebay.get_market_pricing(search_term)
    
    # Generar recomendación
    recommendation = engine.generate_recommendation(
        upc=search_term,
        market_data=market_data,
        internal_data=internal_data
    )
    
    print(f"Precio recomendado: ${recommendation.recommended_price:.2f}")
    print(f"Confianza: {recommendation.confidence_score}/100")
    print(f"Razón: {recommendation.rationale}")
    
    await ebay.close_session()

asyncio.run(main())
```

### 2. Prueba desde API
```bash
curl -X POST http://localhost:8000/price-recommendation \
  -H "Content-Type: application/json" \
  -d '{
    "upc": "Nike Air Max 90",
    "internal_data": null
  }'
```

## Algoritmo de Precios

El motor de recomendación considera:

1. **Sell-through rate interno**
   - \> 0.7 → Mayor peso a precio interno (está funcionando)
   - < 0.7 → Considerar ajuste

2. **Days on shelf**
   - \> 60 días → Reducir precio
   - < 30 días → Precio está bien

3. **Market sample size**
   - < 5 → Baja confianza, mayor peso a interno
   - \> 10 → Alta confianza en mercado

4. **Variación de precio**
   - Diferencia > 30% → Investigar, posible outlier
   - Ajustar por categoría

5. **Categorías**
   - Diferentes márgenes por tipo de producto
   - Métricas históricas por categoría

## Notas Importantes

### Web Scraping de eBay
- ⏱️ Incluye delays aleatorios (2-4 segundos) entre búsquedas
- 🔐 Usa User-Agent personalizado
- 🌐 Sesión persistente para evitar detección
- ⚠️ No abusar del scraping (respetar términos de servicio)

### Datos Internos
- 📊 3,602 registros de 12 semanas de ventas
- 🏷️ Sin UPCs directos → búsqueda por keywords
- 🔍 Búsqueda flexible por brand/category/subcategory
- 💾 Carga en memoria al inicio

### Rendimiento
- 🚀 Cache de resultados de eBay (configurable TTL)
- ⚡ Sesión persistente evita reinicio de navegador
- 📦 Procesamiento de datos internos optimizado con pandas

## Troubleshooting

### Error: "playwright not installed"
```bash
playwright install chromium
```

### Error: "No module named 'ebay_agent_4'"
- Verificar que `ebay_agent_4.py` esté en el directorio raíz
- Verificar que el import path sea correcto

### Error: "CSV file not found"
- Verificar que `thrift_sales_12_weeks_with_subcategory.csv` esté en el directorio raíz
- O especificar path completo en InternalDataProcessor

### eBay scraping bloqueado
- Usar `headless=False` para ver qué pasa
- Aumentar delays entre requests
- Verificar User-Agent
- Considerar usar proxies rotantes

## Próximos Pasos

- [ ] Agregar mapping de UPC a producto (si se obtienen UPCs reales)
- [ ] Implementar rate limiting más sofisticado
- [ ] Agregar más fuentes de market data (Amazon, Mercado Libre, etc.)
- [ ] Dashboard para visualización de decisiones
- [ ] A/B testing de algoritmos de pricing
- [ ] Machine Learning para predicción de sell-through

## Contacto

Para preguntas o issues, revisar los logs en `logs/` o consultar la documentación de la API en `/docs`.
