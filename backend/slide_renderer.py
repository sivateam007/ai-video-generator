"""Render slides as PNG images using Playwright."""
import os, asyncio
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

TEMPLATE_DIR = Path(__file__).parent / "templates"
env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
WIDTH, HEIGHT = 1280, 720

async def render_slides(slides: list[dict], topic: str, output_dir: str, on_progress=None):
    from playwright.async_api import async_playwright

    os.makedirs(output_dir, exist_ok=True)
    template = env.get_template("slide_template.html")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": WIDTH, "height": HEIGHT},
            device_scale_factor=2
        )
        page = await context.new_page()

        for i, slide in enumerate(slides):
            total = len(slides)
            html = template.render(
                topic=topic,
                title=slide.get("title", ""),
                subtitle=slide.get("subtitle", ""),
                bullets=slide.get("bullets", []),
                code=slide.get("code", ""),
                slide_num=f"{i+1:02d} / {total:02d}"
            )
            await page.set_content(html, wait_until="networkidle")
            await page.wait_for_timeout(500)

            out_path = os.path.join(output_dir, f"slide_{i+1:02d}.png")
            await page.screenshot(path=out_path, full_page=False)

            if on_progress:
                await on_progress(f"slide_{i+1:02d}.png")

            print(f"  Slide {i+1:02d} rendered")

        await browser.close()

    return len(slides)
