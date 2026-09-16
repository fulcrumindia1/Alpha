"""
scripts/capture_scrolled_views.py — Capture detailed full-page screenshots of verified state
"""
import os
from playwright.sync_api import sync_playwright

ARTIFACTS_DIR = r"C:\Users\hp\.gemini\antigravity-ide\brain\a076ab33-a190-4446-923f-a531eb7d63c3"

def capture():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(viewport={"width": 1366, "height": 900})
        page.goto("http://localhost:8501")
        page.wait_for_timeout(2000)
        
        # Check for logout
        logout_btn = page.query_selector("button:has-text('Logout')")
        if logout_btn:
            logout_btn.click()
            page.wait_for_timeout(2000)
            
        # Login as Aspirant
        page.fill("input[aria-label='Email Address']", "ravi.kumar@milletfoods.in")
        page.fill("input[aria-label='Password']", "Aspirant@123")
        page.click("button:has-text('LOGIN')")
        page.wait_for_timeout(3000)
        
        # Help / Support tab: scroll to tickets
        page.click("[data-baseweb='tab']:has-text('Help / Support')")
        page.wait_for_timeout(2000)
        page.evaluate("document.querySelector('[data-testid=\\'stAppViewContainer\\']')?.scrollTo(0, 1000)")
        page.wait_for_timeout(1000)
        page.screenshot(path=os.path.join(ARTIFACTS_DIR, "verified_aspirant_ticket_details.png"))
        print("Captured verified_aspirant_ticket_details.png")
        
        # My Journey tab: scroll to timeline
        page.click("[data-baseweb='tab']:has-text('My Journey')")
        page.wait_for_timeout(2000)
        page.screenshot(path=os.path.join(ARTIFACTS_DIR, "verified_aspirant_journey_timeline.png"), full_page=True)
        print("Captured verified_aspirant_journey_timeline.png")
        
        # Logout Aspirant
        page.click("button:has-text('Logout')")
        page.wait_for_timeout(2000)
        
        # Login as Admin
        page.fill("input[aria-label='Email Address']", "admin@fulcrum.in")
        page.fill("input[aria-label='Password']", "Admin@123")
        page.click("button:has-text('LOGIN')")
        page.wait_for_timeout(3000)
        
        # Admin Aspirants & Journeys
        page.click("[data-baseweb='tab']:has-text('Aspirants & Journeys')")
        page.wait_for_timeout(2000)
        page.screenshot(path=os.path.join(ARTIFACTS_DIR, "verified_admin_unified_journey.png"), full_page=True)
        print("Captured verified_admin_unified_journey.png")
        
        browser.close()

if __name__ == "__main__":
    capture()
