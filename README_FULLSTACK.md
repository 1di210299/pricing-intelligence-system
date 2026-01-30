# 🏷️ Sistema de Inteligencia de Precios - Full Stack

Sistema completo de recomendación de precios con **Backend (Python + FastAPI)** y **Frontend (React + Vite)**.

![Architecture](https://img.shields.io/badge/Backend-Python%20%2B%20FastAPI-blue)
![Frontend](https://img.shields.io/badge/Frontend-React%20%2B%20Vite-cyan)
![Data](https://img.shields.io/badge/Data-3600%2B%20Records-green)

## ✨ Características

### Backend
- ✅ **Validación de UPC** (UPC-A 12 dígitos, UPC-E 8 dígitos)
- ✅ **Web Scraping de eBay** (Playwright + sesión persistente)
- ✅ **Procesamiento de datos internos** (3,600+ registros)
- ✅ **Motor de recomendación inteligente**
- ✅ **API REST con FastAPI** + documentación automática
- ✅ **Cache** y **logging** completo

### Frontend
- ✅ **UI moderna y responsive** (React 18)
- ✅ **Búsqueda en tiempo real**
- ✅ **Visualización de métricas** (precio, confianza, weighting)
- ✅ **Gráficos interactivos**
- ✅ **Ejemplos rápidos** para testing
- ✅ **Warnings y alertas** visuales

## 🚀 Quick Start

### Opción 1: Iniciar Todo (Recomendado)
```bash
# Setup e inicio automático de backend + frontend
./start_full.sh
```

Esto iniciará:
- 🔧 Backend en http://localhost:8000
- 🎨 Frontend en http://localhost:3000
- 📚 API Docs en http://localhost:8000/docs

### Opción 2: Iniciar por Separado

**Backend:**
```bash
# Setup
./quick_start.sh

# Iniciar
./start.sh
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## 📸 Capturas de Pantalla

```
┌────────────────────────────────────────────┐
│  🏷️ Pricing Intelligence System           │
│  Sistema de recomendación de precios       │
├────────────────────────────────────────────┤
│                                            │
│  🔍 Buscar Producto                        │
│  ┌──────────────────────────────────────┐ │
│  │ Nike Sneakers                      🔎│ │
│  └──────────────────────────────────────┘ │
│                                            │
│  Ejemplos: [Nike] [Adidas] [Levi's]       │
│                                            │
├────────────────────────────────────────────┤
│  💰 Precio Recomendado                     │
│                                            │
│         $48.50                             │
│     Confianza: 85/100 ✓                    │
│                                            │
├────────────────────────────────────────────┤
│  📊 Mercado    │  📦 Interno  │ 📈 S-T     │
│  $52.00        │  $45.00      │  85%       │
│  15 listings   │  Shoes       │  25 días   │
└────────────────────────────────────────────┘
```

## 📋 Requisitos

- **Backend:**
  - Python 3.10+
  - Playwright (web scraping)
  - Pandas, FastAPI, Uvicorn

- **Frontend:**
  - Node.js 16+
  - npm o yarn

## 🏗️ Arquitectura

```
coding_challenge/
├── frontend/                    # React + Vite
│   ├── src/
│   │   ├── App.jsx             # Componente principal
│   │   ├── main.jsx            # Entry point
│   │   └── index.css           # Estilos
│   ├── package.json
│   └── vite.config.js
│
├── app/                         # Backend FastAPI
│   ├── main.py                 # API endpoints
│   ├── config.py               # Configuración
│   ├── models/                 # Pydantic models
│   ├── services/               # Lógica de negocio
│   │   ├── ebay_client.py     # Web scraper
│   │   ├── internal_data.py   # CSV processor
│   │   ├── pricing_engine.py  # Motor de recomendación
│   │   └── upc_validator.py   # Validador UPC
│   ├── cache/                  # Sistema de cache
│   └── utils/                  # Utilidades
│
├── ebay_agent_4.py             # Playwright scraper
├── thrift_sales_*.csv          # Datos (3,600+ records)
├── tests/                      # Tests unitarios
├── start_full.sh              # Iniciar todo
├── start.sh                   # Solo backend
└── quick_start.sh             # Setup inicial
```

## 🎯 Flujo de Uso

1. **Usuario ingresa búsqueda** → "Nike Sneakers"
2. **Backend procesa:**
   - Valida input
   - Busca en datos internos (CSV)
   - Hace scraping de eBay (precios de mercado)
   - Ejecuta algoritmo de pricing
3. **Frontend muestra:**
   - Precio recomendado con confidence score
   - Weighting (interno vs mercado)
   - Métricas detalladas
   - Explicación de la decisión

## 📊 Algoritmo de Pricing

El sistema considera:

| Factor | Condición | Acción |
|--------|-----------|--------|
| Sell-through | > 70% | ↑ Peso a precio interno |
| Days on shelf | > 60 días | ↓ Reducir precio |
| Market sample | < 5 items | ⚠️ Baja confianza |
| Price variance | > 30% | 🚨 Flag outlier |
| Category | Variable | 📊 Ajuste por margen |

## 🔧 Configuración

### Backend (.env)
```bash
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
CACHE_TYPE=memory
CACHE_TTL=3600
```

### Frontend (.env)
```bash
VITE_API_URL=http://localhost:8000
```

## 📡 API Endpoints

### POST `/price-recommendation`
Obtener recomendación de precio

```json
// Request
{
  "upc": "Nike Air Max 90",
  "internal_data": null
}

// Response
{
  "recommended_price": 48.50,
  "confidence_score": 85,
  "internal_vs_market_weighting": 0.65,
  "rationale": "High sell-through rate...",
  "market_data": { ... },
  "internal_data": { ... },
  "warnings": []
}
```

### GET `/health`
Health check

### GET `/docs`
Documentación interactiva Swagger UI

## 🧪 Testing

```bash
# Test backend (solo datos internos)
python test_integration.py --quick

# Test backend (con eBay scraping)
python test_integration.py

# Tests unitarios
pytest tests/

# Test frontend (manual)
# Abrir http://localhost:3000 y probar ejemplos
```

## 📦 Datos

**CSV de Ventas Internas:**
- 3,600+ items de 12 semanas
- Departamentos: Mens, Womens, Children
- Marcas: Nike, Adidas, Columbia, Levi's, etc.
- Métricas: precio, sell-through, días en stock

**Datos de eBay (scraping):**
- Listings vendidos (últimos 90 días)
- Precios: median, average, min, max
- Sample size y confidence flags

## 🎨 Personalización Frontend

El diseño usa:
- Gradientes morados/azules
- Iconos Lucide React
- CSS vanilla (sin frameworks)
- Responsive design
- Animaciones suaves

Para customizar colores, edita `frontend/src/index.css`:
```css
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
```

## ⚠️ Notas Importantes

### Web Scraping
- ⏱️ Delays automáticos (2-4s entre requests)
- 🔒 Sesión persistente para evitar bloqueos
- ⚠️ Respetar términos de servicio de eBay
- 🚫 No hacer abuse del sistema

### Performance
- 💾 Cache de market data (1 hora default)
- 🚀 Sesión persistente reduce overhead
- 📊 Datos internos pre-cargados en memoria
- ⚡ Frontend con Vite (HMR ultra-rápido)

## 🐛 Troubleshooting

**"Cannot connect to backend"**
```bash
# Verificar que backend esté corriendo
curl http://localhost:8000/health

# Si no, iniciarlo
./start.sh
```

**"Playwright not installed"**
```bash
playwright install chromium
```

**"npm command not found"**
```bash
# Instalar Node.js
brew install node  # macOS
```

**Puerto 3000 ocupado**
```bash
# Cambiar puerto en frontend/vite.config.js
server: { port: 3001 }
```

## 📚 Documentación Adicional

- `INTEGRATION_GUIDE.md` - Guía detallada de integración
- `IMPLEMENTATION_NOTES.md` - Notas técnicas
- `frontend/README.md` - Docs específicas del frontend
- `/docs` - API docs (cuando servidor esté corriendo)

## 🚀 Deploy a Producción

### Backend
```bash
# Usar Gunicorn + Uvicorn workers
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker

# O Docker
docker build -t pricing-api .
docker run -p 8000:8000 pricing-api
```

### Frontend
```bash
cd frontend
npm run build
# Servir dist/ con nginx, vercel, netlify, etc.
```

## 🤝 Contribuir

Este es un proyecto de desafío técnico. Ver archivos de documentación para más detalles.

## 📝 License

MIT

---

**Stack:** Python + FastAPI + React + Vite + Playwright + Pandas  
**Tiempo de desarrollo:** 12-16 horas  
**Última actualización:** Enero 2026

## 🎉 ¡Listo para Usar!

```bash
./start_full.sh
# Abre http://localhost:3000
# Busca "Nike Sneakers"
# ✨ Disfruta!
```
