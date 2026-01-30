# eBay Pricing Agent API (Stateful Edition)

Updated to support **Persistent Sessions**. This allows you to integrate the agent into your own loops and pass keywords one by one WITHOUT closing the browser between calls.

## How to Integrate (Python)

To avoid eBay blocking your IP, you must ensure the browser session stays open while you iterate through your items.

### Correct Pattern ✅
```python
import asyncio
from ebay_agent import EbayPricingAgent

async def main():
    # 1. Initialize Agent
    agent = EbayPricingAgent(headless=False)
    
    # 2. Start Browser Session (Do this ONCE outside your loop)
    await agent.start_session()
    
    my_list = ["Item A", "Item B", "Item C", "Item D"]
    
    # 3. Your Loop
    for keyword in my_list:
        # Pass one string at a time
        data = await agent.get_pricing_data(keyword)
        print(data)
        
    # 4. Close Session (Do this ONCE at the end)
    await agent.close_session()

if __name__ == "__main__":
    asyncio.run(main())

    Incorrect Pattern ❌ (Will get blocked)
Do NOT re-initialize the agent inside the loop.

for keyword in my_list:
    # DON'T DO THIS:
    agent = EbayPricingAgent() 
    await agent.get_pricing_data(keyword) # Opens/Closes browser -> BLOCKED
