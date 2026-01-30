import { useState } from 'react'
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// SVG Icons
const SearchIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
  </svg>
)

const TrendingUpIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/>
  </svg>
)

const TagIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/>
  </svg>
)

const DollarSignIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
    <line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
  </svg>
)

const PackageIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <line x1="16.5" y1="9.4" x2="7.5" y2="4.21"/><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/>
  </svg>
)

const ShoppingCartIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/>
  </svg>
)

const BarChartIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <line x1="12" y1="20" x2="12" y2="10"/><line x1="18" y1="20" x2="18" y2="4"/><line x1="6" y1="20" x2="6" y2="16"/>
  </svg>
)

const AlertTriangleIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
  </svg>
)

const CheckCircleIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>
  </svg>
)

function App() {
  const [searchTerm, setSearchTerm] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)

  const examples = [
    'Nike Sneakers',
    'Adidas Jacket',
    'Levi\'s Jeans',
    'Columbia Jacket',
    'Ralph Lauren Polo'
  ]

  const handleSearch = async (e) => {
    e.preventDefault()
    
    if (!searchTerm.trim()) {
      setError('Please enter a search term')
      return
    }

    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const response = await axios.post(`${API_URL}/price-recommendation`, {
        upc: searchTerm
        // No enviamos internal_data si es null
      })
      
      setResult(response.data)
    } catch (err) {
      console.error('Error:', err.response?.data)
      
      // Manejar diferentes tipos de errores
      let errorMessage = 'Error getting recommendation. Please verify the server is running.'
      
      if (err.response?.data?.detail) {
        const detail = err.response.data.detail
        
        // Si detail es un array (errores de validación)
        if (Array.isArray(detail)) {
          errorMessage = detail.map(e => e.msg).join(', ')
        } 
        // Si detail es un string
        else if (typeof detail === 'string') {
          errorMessage = detail
        }
      }
      
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  const handleExampleClick = (example) => {
    setSearchTerm(example)
  }

  const getConfidenceColor = (score) => {
    if (score >= 80) return '#10b981'
    if (score >= 60) return '#f59e0b'
    return '#ef4444'
  }

  return (
    <div className="container">
      <div className="header">
        <h1>
          <TagIcon />
          Pricing Intelligence System
        </h1>
        <p>Price recommendation system based on market and internal data</p>
      </div>

      <div className="card">
        <form onSubmit={handleSearch}>
          <div className="input-group">
            <label htmlFor="search">Search Product (UPC, Brand, Category)</label>
            <div className="input-wrapper">
              <div className="input-icon">
                <SearchIcon />
              </div>
              <input
                id="search"
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="e.g., Nike Air Max 90, 012345678905"
                disabled={loading}
              />
            </div>
          </div>

          <button type="submit" className="btn btn-primary" disabled={loading}>
            {loading ? (
              <>
                <div className="spinner"></div>
                Analyzing...
              </>
            ) : (
              <>
                <TrendingUpIcon />
                Get Price Recommendation
              </>
            )}
          </button>
        </form>

        <div className="examples">
          <h4>Quick Examples</h4>
          <div className="example-tags">
            {examples.map((example) => (
              <div
                key={example}
                className="example-tag"
                onClick={() => handleExampleClick(example)}
              >
                {example}
              </div>
            ))}
          </div>
        </div>
      </div>

      {error && (
        <div className="card">
          <div className="error">
            <AlertTriangleIcon />
            <span>{error}</span>
          </div>
        </div>
      )}

      {loading && (
        <div className="card">
          <div className="loading">
            <div className="spinner"></div>
            <p>Analyzing market data and internal sales...</p>
          </div>
        </div>
      )}

      {result && (
        <div className="result-section">
          <div className="card">
            <div className="price-display">
              <h2>Recommended Price</h2>
              <div className="price">${result.recommended_price.toFixed(2)}</div>
              <div 
                className="confidence-badge"
                style={{ 
                  background: `${getConfidenceColor(result.confidence_score)}20`, 
                  color: getConfidenceColor(result.confidence_score),
                  border: `1px solid ${getConfidenceColor(result.confidence_score)}40`
                }}
              >
                <CheckCircleIcon />
                Confidence: {result.confidence_score}/100
              </div>
            </div>

            <div className="metrics-grid">
              {result.market_data && result.market_data.sample_size > 0 && (
                <>
                  <div className="metric-card">
                    <h3><ShoppingCartIcon /> Market (eBay)</h3>
                    <div className="value">${result.market_data.median_price?.toFixed(2) || 'N/A'}</div>
                    <div className="sub-text">{result.market_data.sample_size} listings</div>
                  </div>

                  <div className="metric-card">
                    <h3><BarChartIcon /> Range</h3>
                    <div className="value" style={{fontSize: '1.1rem'}}>
                      ${result.market_data.min_price?.toFixed(2)} - ${result.market_data.max_price?.toFixed(2)}
                    </div>
                  </div>
                </>
              )}

              {result.internal_data && (
                <>
                  <div className="metric-card">
                    <h3><PackageIcon /> Internal Price</h3>
                    <div className="value">${result.internal_data.internal_price.toFixed(2)}</div>
                    <div className="sub-text">{result.internal_data.category}</div>
                  </div>

                  <div className="metric-card">
                    <h3><TrendingUpIcon /> Sell-Through</h3>
                    <div className="value">{(result.internal_data.sell_through_rate * 100).toFixed(1)}%</div>
                    <div className="sub-text">{result.internal_data.days_on_shelf} days</div>
                  </div>
                </>
              )}
            </div>

            <div className="weight-bar">
              <h3>Data Sources Weight</h3>
              <div className="weight-bar-container">
                <div 
                  className="weight-bar-internal" 
                  style={{ width: `${result.internal_vs_market_weighting * 100}%` }}
                >
                  {result.internal_vs_market_weighting > 0.15 && 
                    `Internal ${(result.internal_vs_market_weighting * 100).toFixed(0)}%`
                  }
                </div>
                <div 
                  className="weight-bar-market" 
                  style={{ width: `${(1 - result.internal_vs_market_weighting) * 100}%` }}
                >
                  {result.internal_vs_market_weighting < 0.85 && 
                    `Market ${((1 - result.internal_vs_market_weighting) * 100).toFixed(0)}%`
                  }
                </div>
              </div>
            </div>

            <div className="rationale-box">
              <h3>Decision Explanation</h3>
              <p>{result.rationale}</p>
            </div>

            {result.warnings && result.warnings.length > 0 && (
              <div className="warning-box">
                <h4><AlertTriangleIcon /> Warnings</h4>
                <ul>
                  {result.warnings.map((warning, idx) => (
                    <li key={idx}>{warning}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}

      {!result && !loading && !error && (
        <div className="card empty-state">
          <DollarSignIcon />
          <h3>Enter a product to get started</h3>
          <p>The system will analyze market data (eBay) and internal sales to generate an optimal price recommendation</p>
        </div>
      )}
    </div>
  )
}

export default App
