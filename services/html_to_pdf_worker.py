"""
services/html_to_pdf_worker.py — Subprocess Playwright Worker
=============================================================
Runs Playwright inside an isolated subprocess, completely detached from
Streamlit's asyncio loop and thread-local state.
Renders pixel-perfect A4 PDFs with Google Fonts Montserrat and print background.
"""

import sys
import os
from playwright.sync_api import sync_playwright

def convert_html_to_pdf(input_html_path: str, output_pdf_path: str) -> bool:
    with open(input_html_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    with sync_playwright() as p:
        browser = None
        try:
            browser = p.chromium.launch(channel="chrome", headless=True)
        except Exception:
            browser = p.chromium.launch(headless=True)

        page = browser.new_page()
        page.set_content(html_content, wait_until="networkidle", timeout=30000)
        page.pdf(
            path=output_pdf_path,
            format="A4",
            print_background=True,
            display_header_footer=True,
            header_template="<span></span>",
            footer_template="""
            <div style="font-family:Montserrat,sans-serif;font-size:8px;color:#94A3B8;width:100%;text-align:center;padding:0 40px;">
                <span>FULCRUM-INDIA Confidential · Enterprise Guidance System Dossier</span>
                <span style="float:right;">Page <span class="pageNumber"></span> of <span class="totalPages"></span></span>
            </div>""",
            margin={
                "top": "18mm",
                "bottom": "20mm",
                "left": "15mm",
                "right": "15mm"
            }
        )
        browser.close()

    return os.path.exists(output_pdf_path) and os.path.getsize(output_pdf_path) > 1000

def main():
    if len(sys.argv) < 3:
        sys.stderr.write("Usage: python html_to_pdf_worker.py <input_html_path> <output_pdf_path>\n")
        sys.exit(1)

    input_html = sys.argv[1]
    output_pdf = sys.argv[2]

    try:
        success = convert_html_to_pdf(input_html, output_pdf)
        if success:
            sys.stdout.write("OK\n")
            sys.exit(0)
        else:
            sys.stderr.write("Conversion failed: Output PDF missing or empty\n")
            sys.exit(2)
    except Exception as e:
        sys.stderr.write(f"Worker exception: {e}\n")
        sys.exit(3)

if __name__ == "__main__":
    main()
