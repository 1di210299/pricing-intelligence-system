# Pricing Intelligence System - Frontend

Frontend en React + Vite para el sistema de inteligencia de precios.

## 🚀 Quick Start

```bash
# Instalar dependencias
npm install

# Iniciar en desarrollo
npm run dev

# Build para producción
npm run build
```

## 🔧 Configuración

1. Copiar `.env.example` a `.env`
2. Configurar la URL del API backend (default: http://localhost:8000)

## 📦 Tecnologías

- React 18
- Vite
- Axios
- Lucide React (iconos)

## 🎨 Características

- ✅ Búsqueda de productos por UPC, marca o categoría
- ✅ Visualización del precio recomendado con confidence score
- ✅ Gráfico de weighting (interno vs mercado)
- ✅ Detalles de datos de mercado (eBay) e internos
- ✅ Explicación detallada de la decisión (rationale)
- ✅ Alertas y warnings
- ✅ Ejemplos rápidos para testing
- ✅ UI moderna y responsive

## 🌐 Uso

1. Asegúrate de que el backend esté corriendo: `./start.sh` en el directorio raíz
2. Inicia el frontend: `npm run dev`
3. Abre http://localhost:3000
4. Ingresa un término de búsqueda (ej: "Nike Sneakers")
5. Visualiza la recomendación de precio generada

## 📝 Proxy API

El frontend incluye un proxy configurado en `vite.config.js` que redirige `/api/*` a `http://localhost:8000`. Esto evita problemas de CORS durante el desarrollo.
