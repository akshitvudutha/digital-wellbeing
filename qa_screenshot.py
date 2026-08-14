import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(color_scheme="dark")
        page = await context.new_page()
        
        viewports = [
            {"width": 1920, "height": 1080, "name": "1920x1080"},
            {"width": 1440, "height": 900, "name": "1440x900"},
            {"width": 768, "height": 1024, "name": "768x1024"},
            {"width": 390, "height": 844, "name": "390x844"},
        ]
        
        for vp in viewports:
            await page.set_viewport_size({"width": vp["width"], "height": vp["height"]})
            await page.goto("http://localhost:3000")
            # Wait for any animations to settle
            await page.wait_for_timeout(2000)
            
            await page.screenshot(path=f"screenshot_{vp['name']}.png", full_page=True)
            print(f"Captured {vp['name']}")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
