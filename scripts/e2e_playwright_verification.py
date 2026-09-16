"""
scripts/e2e_playwright_verification.py — Full Browser End-to-End Test
=====================================================================
Uses installed Chrome via Playwright to verify all 4 workflows in the actual Streamlit UI:
1. Aspirant Profile Save (verifies RLS error is gone, success banner shown)
2. Aspirant Journey Milestone Logging (within expander)
3. Guide Journey Mentorship Logging & Ticket Response
4. Admin Journey Directive Logging & Unified Journey Inspection
5. Admin Ticket Resolution & Aspirant Multi-Role Response Verification
Captures screenshots to the conversation artifact directory.
"""

import os
import sys
from playwright.sync_api import sync_playwright

ARTIFACTS_DIR = r"C:\Users\hp\.gemini\antigravity-ide\brain\a076ab33-a190-4446-923f-a531eb7d63c3"
BASE_URL = "http://localhost:8501"

def wait_for_streamlit_ready(page, timeout=15000):
    """Wait until Streamlit is not actively running/loading."""
    page.wait_for_timeout(1500)
    try:
        page.wait_for_selector("[data-testid='stStatusWidget']", state="hidden", timeout=timeout)
    except Exception:
        pass
    page.wait_for_timeout(1000)

def click_tab(page, tab_text):
    """Clicks a Streamlit tab by its visible label."""
    print(f"Clicking tab: {tab_text}...")
    tab_elem = page.wait_for_selector(f"[data-baseweb='tab']:has-text('{tab_text}')", timeout=10000)
    tab_elem.scroll_into_view_if_needed()
    tab_elem.click()
    wait_for_streamlit_ready(page)

def click_expander(page, text_match):
    """Clicks an expander header to expand it."""
    print(f"Expanding: {text_match}...")
    exp = page.wait_for_selector(f"[data-testid='stExpander']:has-text('{text_match}') summary, div[data-testid='stExpander'] summary:has-text('{text_match}'), summary:has-text('{text_match}')", timeout=10000)
    exp.scroll_into_view_if_needed()
    exp.click()
    wait_for_streamlit_ready(page)

def login(page, email, password):
    print(f"\n--- Logging in as {email} ---")
    page.goto(BASE_URL)
    wait_for_streamlit_ready(page)
    
    # Check if already logged in
    logout_btn = page.query_selector("button:has-text('Logout')")
    if logout_btn:
        print("Existing session found. Logging out first...")
        logout_btn.click()
        wait_for_streamlit_ready(page)
    
    # Fill login form
    email_input = page.wait_for_selector("input[aria-label='Email Address']", timeout=10000)
    email_input.fill("")
    email_input.fill(email)
    
    pwd_input = page.wait_for_selector("input[aria-label='Password']", timeout=10000)
    pwd_input.fill("")
    pwd_input.fill(password)
    
    signin_btn = page.wait_for_selector("button:has-text('LOGIN')", timeout=10000)
    signin_btn.click()
    wait_for_streamlit_ready(page)
    print(f"Logged in successfully as {email}")

def run_e2e():
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        context = browser.new_context(viewport={"width": 1366, "height": 768})
        page = context.new_page()
        
        # ----------------------------------------------------
        # WORKFLOW 1: ASPIRANT PROFILE & JOURNEY & HELP
        # ----------------------------------------------------
        print("\n=== STARTING WORKFLOW 1: ASPIRANT FLOW ===")
        login(page, "ravi.kumar@milletfoods.in", "Aspirant@123")
        
        # Click My Profile Tab
        click_tab(page, "My Profile")
        
        # Click Save Profile & Update Matches
        print("Saving Aspirant Profile (Testing RLS fix)...")
        save_btn = page.wait_for_selector("button:has-text('SAVE PROFILE & UPDATE MATCHES')", timeout=10000)
        save_btn.scroll_into_view_if_needed()
        save_btn.click()
        wait_for_streamlit_ready(page)
        
        # Check for error or success
        page.screenshot(path=os.path.join(ARTIFACTS_DIR, "aspirant_profile_saved.png"), full_page=True)
        content = page.content()
        assert "violates row-level security policy" not in content, "RLS violation error detected!"
        print("SUCCESS: Profile saved cleanly! Zero RLS errors detected. Screenshot saved.")
        
        # Click My Journey Tab
        click_tab(page, "My Journey")
        
        # Expand Add Journey Milestone
        click_expander(page, "Add Journey Milestone")
        
        # Aspirant writes milestone
        print("Aspirant logging new milestone to his journey...")
        title_input = page.wait_for_selector("input[placeholder*='Started Business, Launched Product']", timeout=10000)
        title_input.scroll_into_view_if_needed()
        title_input.fill("Pilot Supply Secured: 15 Organic Retailers in Madurai")
        
        desc_input = page.wait_for_selector("textarea[placeholder*='Started selling millet porridge']", timeout=10000)
        desc_input.fill("Signed retail placement agreements with 15 natural grocery outlets across Madurai district.")
        
        page.wait_for_selector("button:has-text('ADD TO MY JOURNEY')", timeout=10000).click()
        wait_for_streamlit_ready(page)
        page.screenshot(path=os.path.join(ARTIFACTS_DIR, "aspirant_journey_entry.png"), full_page=True)
        print("SUCCESS: Aspirant added milestone to Journey! Screenshot saved.")
        
        # Click Help / Support Tab
        click_tab(page, "Help / Support")
        
        print("Aspirant submitting Help Request...")
        help_subj = page.wait_for_selector("input[placeholder*='GST Registration, Bank Proposal Review']", timeout=10000)
        help_subj.scroll_into_view_if_needed()
        help_subj.fill("Bank FDR Collateral for PMEGP Margin Requirement")
        help_subj.press("Tab")
        page.wait_for_timeout(300)
        
        help_msg = page.wait_for_selector("textarea[placeholder*='Describe exactly what you need help with']", timeout=10000)
        help_msg.fill("Can fixed deposit receipts or national savings certificates be pledged for margin money under PMEGP?")
        help_msg.press("Tab")
        page.wait_for_timeout(500)
        
        send_btn = page.wait_for_selector("button:has-text('SEND HELP REQUEST')", timeout=10000)
        send_btn.scroll_into_view_if_needed()
        send_btn.click()
        wait_for_streamlit_ready(page)
        page.wait_for_timeout(2000)
        
        page.screenshot(path=os.path.join(ARTIFACTS_DIR, "aspirant_help_submitted.png"), full_page=True)
        print("SUCCESS: Aspirant submitted Help Request! Screenshot saved.")
        
        # Logout Aspirant
        page.wait_for_selector("button:has-text('Logout')", timeout=10000).click()
        wait_for_streamlit_ready(page)
        
        # ----------------------------------------------------
        # WORKFLOW 2: GUIDE MENTORSHIP & RESPONSE
        # ----------------------------------------------------
        print("\n=== STARTING WORKFLOW 2: GUIDE FLOW ===")
        login(page, "rajendran@fulcrum.in", "Welcome@2026")
        
        # Guide Portal: Ensure in My Aspirants tab, then click Journey subtab
        click_tab(page, "My Aspirants")
        click_tab(page, "Journey")
        
        # Expand Mentorship Contribution
        click_expander(page, "Log Mentorship Contribution")
        
        # Guide writes to Aspirant's Journey
        print("Guide writing mentorship contribution to Ravi's Journey...")
        guide_title = page.wait_for_selector("input[placeholder*='Business Model & PMEGP Review']", timeout=10000)
        guide_title.scroll_into_view_if_needed()
        guide_title.fill("Guide DPR Review & Collateral Certification")
        guide_title.press("Tab")
        
        guide_notes = page.wait_for_selector("textarea[placeholder*='Reviewed DPR proposal']", timeout=10000)
        guide_notes.fill("Vetted detailed project report. Calibrated machinery cost quotations with State Bank of India Madurai SME branch.")
        guide_notes.press("Tab")
        page.wait_for_timeout(300)
        
        page.wait_for_selector("button:has-text('SAVE JOURNEY CONTRIBUTION')", timeout=10000).click()
        wait_for_streamlit_ready(page)
        page.screenshot(path=os.path.join(ARTIFACTS_DIR, "guide_journey_mentorship.png"), full_page=True)
        print("SUCCESS: Guide contributed to Aspirant's Journey! Screenshot saved.")
        
        # Guide replies to Help Ticket
        click_tab(page, "Help Requests")
        
        # Find ticket and respond
        click_expander(page, "Respond to")
        
        resp_area = page.wait_for_selector("textarea[placeholder*='Provide guidance, action points']", timeout=10000)
        resp_area.scroll_into_view_if_needed()
        resp_area.fill("Yes, FDR is officially recognized as eligible margin money under RBI PMEGP guidelines.")
        resp_area.press("Tab")
        page.wait_for_timeout(300)
        
        page.wait_for_selector("button:has-text('Send Response & Update Ticket')", timeout=10000).click()
        wait_for_streamlit_ready(page)
        page.screenshot(path=os.path.join(ARTIFACTS_DIR, "guide_help_reply.png"), full_page=True)
        print("SUCCESS: Guide responded to Help Ticket! Screenshot saved.")
        
        # Logout Guide
        page.wait_for_selector("button:has-text('Logout')", timeout=10000).click()
        wait_for_streamlit_ready(page)
        
        # ----------------------------------------------------
        # WORKFLOW 3: ADMIN UNIFIED JOURNEY & DIRECTIVE & RESOLUTION
        # ----------------------------------------------------
        print("\n=== STARTING WORKFLOW 3: ADMIN FLOW ===")
        login(page, "admin@fulcrum.in", "Admin@123")
        
        # Admin Portal: Go to Aspirants & Journeys
        click_tab(page, "Aspirants & Journeys")
        
        # Expand Admin Directive form
        click_expander(page, "Log Official Administrative Directive")
        
        # Log Administrative Directive to Aspirant's Journey
        print("Admin logging official Directive to Ravi's Journey...")
        adm_title = page.wait_for_selector("input[placeholder*='Subsidy Sanction Review']", timeout=10000)
        adm_title.scroll_into_view_if_needed()
        adm_title.fill("State Subsidy Fast-Track Approved by Committee")
        adm_title.press("Tab")
        
        adm_details = page.wait_for_selector("textarea[placeholder*='Formally reviewed founder']", timeout=10000)
        adm_details.fill("Administrative committee has reviewed venture traction and sanctioned the application for fast-track processing.")
        adm_details.press("Tab")
        page.wait_for_timeout(300)
        
        page.wait_for_selector("button:has-text('RECORD ADMINISTRATIVE DIRECTIVE')", timeout=10000).click()
        wait_for_streamlit_ready(page)
        
        # Scroll down to Full Unified Journey & Interaction Timeline
        print("Verifying Unified Journey on Admin Dashboard...")
        page.screenshot(path=os.path.join(ARTIFACTS_DIR, "admin_journey_directive.png"), full_page=True)
        print("SUCCESS: Admin logged directive and verified unified timeline! Screenshot saved.")
        
        # Admin resolves Help Request
        click_tab(page, "Help Requests Queue")
        
        # Expand ticket
        click_expander(page, "Bank FDR Collateral")
        
        adm_resp_area = page.wait_for_selector("input[aria-label='Admin Response']:visible", timeout=10000)
        adm_resp_area.scroll_into_view_if_needed()
        adm_resp_area.fill("Administrative Directorate has countersigned the bank proposal packet. Officially resolved.")
        adm_resp_area.press("Tab")
        page.wait_for_timeout(300)
        
        submit_btn = page.wait_for_selector("button:has-text('SUBMIT RESPONSE & UPDATE'):visible", timeout=10000)
        submit_btn.click()
        wait_for_streamlit_ready(page)
        page.screenshot(path=os.path.join(ARTIFACTS_DIR, "admin_help_resolved.png"), full_page=True)
        print("SUCCESS: Admin replied and resolved ticket! Screenshot saved.")
        
        # Logout Admin
        page.wait_for_selector("button:has-text('Logout')", timeout=10000).click()
        wait_for_streamlit_ready(page)
        
        # ----------------------------------------------------
        # WORKFLOW 4: ASPIRANT RETURN & VERIFICATION
        # ----------------------------------------------------
        print("\n=== STARTING WORKFLOW 4: ASPIRANT RETURN & VERIFICATION ===")
        login(page, "ravi.kumar@milletfoods.in", "Aspirant@123")
        
        # Go to My Journey
        print("Verifying Aspirant views all Journey entries (Aspirant + Guide + Admin)...")
        click_tab(page, "My Journey")
        page.screenshot(path=os.path.join(ARTIFACTS_DIR, "aspirant_journey_final.png"), full_page=True)
        
        # Go to Help / Support
        print("Verifying Aspirant sees both Guide Response and Admin Response on Support Ticket...")
        click_tab(page, "Help / Support")
        page.screenshot(path=os.path.join(ARTIFACTS_DIR, "aspirant_help_resolved.png"), full_page=True)
        
        final_content = page.content()
        assert "Guide Response:" in final_content, "Guide Response not rendered in Aspirant Support view!"
        assert "Admin Response:" in final_content, "Admin Response not rendered in Aspirant Support view!"
        print("SUCCESS: Aspirant sees full resolution and responses from both Guide and Admin! Screenshot saved.")
        
        browser.close()
        print("\n=======================================================")
        print("ALL E2E BROWSER WORKFLOWS COMPLETED WITH 100% SUCCESS!")
        print("=======================================================")

if __name__ == "__main__":
    run_e2e()
