import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        
        # Test 1: No forced preference
        context1 = await browser.new_context()
        page1 = await context1.new_page()
        await page1.goto("http://localhost:3000")
        await page1.wait_for_timeout(1000)
        await page1.screenshot(path="theme_none.png")
        await context1.close()
        
        # Test 2: prefers-color-scheme: light
        context2 = await browser.new_context(color_scheme="light")
        page2 = await context2.new_page()
        await page2.goto("http://localhost:3000")
        await page2.wait_for_timeout(1000)
        await page2.screenshot(path="theme_light.png")
        await context2.close()
        
        # Test 3: prefers-color-scheme: dark
        context3 = await browser.new_context(color_scheme="dark")
        page3 = await context3.new_page()
        await page3.goto("http://localhost:3000")
        await page3.wait_for_timeout(1000)
        await page3.screenshot(path="theme_dark.png")
        await context3.close()
        
        await browser.close()
        print("Done capturing themes.")

if __name__ == "__main__":
    asyncio.run(main())
