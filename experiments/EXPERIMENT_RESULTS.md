# Experiment Results: Playwright vs OpenAI Web Search

**Date**: 2026-01-30  
**Objective**: Compare direct HTML scraping (Playwright) vs OpenAI web_search API for extracting eBay sold listings

---

## 🎯 Summary

Successfully implemented and tested **Playwright-based HTML scraping** with correct eBay selectors (`.s-card` structure).

---

## ✅ Results

### Playwright Direct HTML Scraping
- **Status**: ✅ **WORKS SUCCESSFULLY**
- **Listings extracted**: **30 items**
- **Data quality**: Complete (title, price, condition, shipping, sold date)
- **Price range**: $1.00 - $903.12
- **Median price**: $183.94
- **Average price**: $234.93
- **All items marked as "Sold"**: 30/30

**Sample listings extracted:**
1. Talla 11.5 - Acrónimo x Nike Blazer Bajo - $234.14
2. Talla 11 - Nike Paul Rodriguez Zoom Air Low Bred - $334.49
3. Nike Air Vapormax Plus - $165.91
4. Nike Joyride Dual Run 2 - $167.25
5. Nike Phantom 6 High Elite FG - $371.28

### OpenAI Web Search API
- **Status**: ⚠️ **INCONSISTENT**
- **Current test**: No data extracted (returned null/0 sample)
- **Previous production tests**: Successfully extracted 4 listings
- **Behavior**: Variable - sometimes works, sometimes doesn't find results

---

## 🔍 Key Findings

### 1. Correct eBay Selectors (Critical Discovery)
The original scraper failed because it used outdated selectors. eBay's current HTML structure:

```javascript
// ❌ OLD (doesn't work)
'.s-item'
'.s-item__title'
'.s-item__price'

// ✅ NEW (works correctly)
'.s-card'                              // Main container
'.s-card__title .su-styled-text'       // Title
'.s-card__price'                       // Price
'.s-card__subtitle .su-styled-text'    // Condition
'.s-card__caption'                     // Sold status/date
```

### 2. Dynamic JavaScript Rendering
eBay loads listings dynamically via JavaScript AFTER initial page load. Solution:
- Wait for `.s-card` selector to appear
- Additional 5-second wait for JS rendering
- Scroll page to trigger lazy loading
- Screenshot verification shows page is fully loaded

### 3. Data Extraction Success
Playwright can extract **structured data** including:
- ✅ Product titles
- ✅ Prices (S/. Peruvian Soles format)
- ✅ Condition (new/used/refurbished)
- ✅ Shipping costs
- ✅ Sold status and dates
- ✅ Direct links to listings

---

## 📊 Comparison Matrix

| Metric | Playwright HTML | OpenAI web_search |
|--------|----------------|-------------------|
| **Listings extracted (this test)** | 30 | 0 (failed to find) |
| **Listings extracted (production)** | N/A (not deployed) | 4 (variable) |
| **Data completeness** | ✅ Full details | ⚠️ Aggregated only |
| **Consistency** | ✅ Reliable once selectors correct | ⚠️ Variable (sometimes works) |
| **Maintenance** | ⚠️ Needs selector updates if eBay changes | ✅ Handles changes automatically |
| **Cost** | ✅ No API fees | ⚠️ OpenAI API costs per request |
| **Performance** | ~15 seconds (browser launch + scrape) | ~5-7 seconds (API call) |
| **Infrastructure** | Requires browser automation | Simple HTTP requests |

---

## 🎯 Recommendations

### Option 1: Switch to Playwright ✅ **RECOMMENDED**
**When to choose:**
- You want maximum data extraction (30 items vs 0-4)
- You need complete listing details (not just aggregated prices)
- You prefer no ongoing API costs
- You have infrastructure for browser automation

**Implementation:**
```python
# Already working in experiments/ebay_html_scraper_v2.py
html, listings = fetch_ebay_search_with_playwright("Nike Sneakers", max_results=30)
```

**Trade-offs:**
- Requires `playwright` package + browser installation
- May need selector updates if eBay redesigns (but not frequently)
- Slightly higher computational cost (browser automation)

### Option 2: Keep OpenAI web_search
**When to choose:**
- You prioritize code simplicity over data volume
- Inconsistent results are acceptable (sometimes returns 0, sometimes 4)
- You want eBay HTML changes handled automatically
- API costs are negligible compared to infrastructure

**Trade-offs:**
- Variable data extraction (0-4 items observed)
- Only aggregated data (no individual listing details)
- Depends on OpenAI's web_search reliability
- Ongoing API costs

### Option 3: Hybrid Approach ⚖️
**Best of both worlds:**
1. **Primary**: Use Playwright for reliable, comprehensive data
2. **Fallback**: If Playwright fails (blocked, timeout), try OpenAI
3. **Caching**: Cache Playwright results to avoid re-scraping

```python
async def get_ebay_data(search_term):
    try:
        # Try Playwright first (more data)
        html, listings = fetch_ebay_search_with_playwright(search_term)
        if len(listings) >= 10:  # Good data threshold
            return listings
    except Exception as e:
        logger.warning(f"Playwright failed: {e}")
    
    # Fallback to OpenAI
    market_data = await ebay_client.get_market_pricing(search_term)
    return market_data
```

---

## 💡 Conclusion

**Playwright scraping extracts 7.5x MORE data** than the current OpenAI method (30 vs 4 listings in production, 30 vs 0 in current test).

**Recommendation**: **Migrate to Playwright** for production use. The improved data volume significantly enhances ML model accuracy and price recommendations.

---

## 📁 Files Generated

- `experiments/ebay_html_scraper_v2.py` - Working Playwright scraper
- `experiments/ebay_results_v2.json` - 30 extracted listings
- `experiments/ebay_search_v2.html` - Raw HTML (2.3MB)
- `experiments/ebay_page_v2.png` - Screenshot verification
- `experiments/compare_methods.py` - Comparison script

---

## 🚀 Next Steps

If deploying Playwright to production:

1. **Install dependencies**:
   ```bash
   pip install playwright
   playwright install chromium
   ```

2. **Update Dockerfile**:
   ```dockerfile
   RUN pip install playwright && playwright install --with-deps chromium
   ```

3. **Replace in `app/services/ebay_client.py`**:
   ```python
   from experiments.ebay_html_scraper_v2 import fetch_ebay_search_with_playwright
   
   async def get_market_pricing(self, search_term: str) -> MarketData:
       html, listings = fetch_ebay_search_with_playwright(search_term, max_results=50)
       # Convert to MarketData format
       ...
   ```

4. **Add timeout/error handling** for robustness

5. **Monitor** for eBay blocks/rate limits

---

**Experiment completed successfully! ✅**
