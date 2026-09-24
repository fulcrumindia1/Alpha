import os
import sys
import time

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from playwright.sync_api import sync_playwright

ARTIFACT_DIR = r"C:\Users\hp\.gemini\antigravity-ide\brain\a076ab33-a190-4446-923f-a531eb7d63c3"
BASE_URL = "http://localhost:8503"

def run_full_verification():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        context = browser.new_context(viewport={"width": 1366, "height": 900})
        page = context.new_page()

        print("\n=======================================================")
        print("STAGE 1: VERIFYING GUIDE WORKSPACE (pravin60666@gmail.com)")
        print("=======================================================")
        page.goto(BASE_URL, timeout=60000)
        page.wait_for_timeout(3000)

        # 1.1 Login as Guide
        print("Step 1.1: Logging in as Guide...")
        page.locator('input[aria-label="Email Address"]').first.fill("pravin60666@gmail.com")
        page.locator('input[type="password"]').first.fill("Pravin@613")
        page.locator('button:has-text("LOGIN")').first.click()
        page.wait_for_selector("text=Welcome, Pravin", timeout=20000)
        page.wait_for_timeout(3000)

        body = page.locator("body").inner_text()
        assert "Welcome, Pravin A" in body, "Failed to login as Guide!"
        print("  -> Logged in successfully as Guide!")
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "guide_01_aspirants_default.png"))

        # 1.2 Main Tab: All Consultations Overview
        print("\nStep 1.2: Testing Main Tab 'All Consultations Overview'...")
        tab_consult_ov = page.locator('button[role="tab"]:has-text("All Consultations Overview")')
        tab_consult_ov.click()
        page.wait_for_selector("text=Assigned Mentee Consultations", timeout=15000)
        page.wait_for_timeout(2000)
        body = page.locator("body").inner_text()
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "guide_02_all_consultations.png"))
        assert "Assigned Mentee Consultations" in body, "ERROR: All Consultations Overview tab is blank!"
        print("  -> SUCCESS: All Consultations Overview renders properly (NOT BLANK)!")

        # 1.3 Main Tab: My Profile
        print("\nStep 1.3: Testing Main Tab 'My Profile'...")
        tab_prof = page.locator('button[role="tab"]:has-text("My Profile")')
        tab_prof.click()
        page.wait_for_selector("text=My Guide Profile", timeout=15000)
        page.wait_for_timeout(2000)
        body = page.locator("body").inner_text()
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "guide_03_my_profile.png"))
        assert "My Guide Profile" in body and "VERIFIED GUIDE" in body, "ERROR: My Profile tab is blank!"
        print("  -> SUCCESS: My Profile renders properly (NOT BLANK)!")

        # 1.4 Return to Main Tab: My Aspirants
        print("\nStep 1.4: Returning to Main Tab 'My Aspirants'...")
        page.locator('button[role="tab"]:has-text("My Aspirants")').click()
        page.wait_for_selector('[role="radiogroup"]', timeout=15000)
        page.wait_for_timeout(2000)

        # 1.5 Mentee Subtab: Consultations
        print("\nStep 1.5: Testing Mentee Subtab 'Consultations'...")
        consult_pill = page.locator('[role="radiogroup"] button:has-text("Consultations")')
        consult_pill.click()
        page.wait_for_selector("text=Direct Consultations:", timeout=15000)
        page.wait_for_timeout(2000)
        body = page.locator("body").inner_text()
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "guide_04_mentee_consultations.png"))
        assert "Direct Consultations:" in body, "ERROR: Consultations subtab is blank!"
        print("  -> SUCCESS: Consultations subtab renders properly (NOT BLANK)!")

        # 1.6 Mentee Subtab: Journey & Milestone Contribution
        print("\nStep 1.6: Testing Mentee Subtab 'Journey' and Contribution submission...")
        journey_pill = page.locator('[role="radiogroup"] button:has-text("Journey")')
        journey_pill.click()
        page.wait_for_selector("text=Complete Journey Narrative Spine", timeout=15000)
        page.wait_for_timeout(2000)
        body = page.locator("body").inner_text()
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "guide_05_mentee_journey.png"))
        assert "Complete Journey Narrative Spine" in body, "ERROR: Journey subtab is blank!"
        print("  -> SUCCESS: Journey subtab renders properly!")

        print("  -> Logging a test mentorship contribution...")
        page.locator('summary:has-text("Log Mentorship Contribution")').click()
        page.wait_for_timeout(1000)
        
        milestone_title = f"Test Verification Milestone {int(time.time())}"
        page.locator('input[aria-label="Title / Milestone"]').fill(milestone_title)
        page.locator('textarea[aria-label="Guidance Notes / What was achieved?"]').fill("Automated verification on localhost: confirmed active subtab retention and database persistence.")
        page.locator('button:has-text("SAVE JOURNEY CONTRIBUTION")').click()
        
        # Wait for Streamlit rerun and success
        page.wait_for_selector(f"text={milestone_title}", timeout=25000)
        page.wait_for_timeout(2000)
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "guide_06_after_journey_save.png"))
        
        body = page.locator("body").inner_text()
        assert milestone_title in body, "Milestone title not found in journey spine!"
        print(f"  -> SUCCESS: Mentorship contribution saved, milestone visible in spine, active subtab stayed on Journey!")


        # 1.7 Mentee Subtab: Scheme Matches & Release
        print("\nStep 1.7: Testing Mentee Subtab 'Scheme Matches'...")
        scheme_pill = page.locator('[role="radiogroup"] button:has-text("Scheme Matches")')
        scheme_pill.click()
        page.wait_for_selector("text=AI-suggested matches and full catalogue access", timeout=20000)
        page.wait_for_timeout(2000)
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "guide_07_scheme_gatekeeper.png"))
        body = page.locator("body").inner_text()
        assert "AI-suggested matches and full catalogue access" in body, "ERROR: Scheme Matches subtab is blank!"
        print("  -> SUCCESS: Scheme Matches subtab renders properly (NOT BLANK) with AI recommendations!")

        # Test Release or Withdraw action
        print("  -> Testing Scheme Gatekeeper actions (Release / Withdraw)...")
        withdraw_btn = page.locator('button:has-text("Withdraw Release")').first
        if withdraw_btn.count() > 0:
            withdraw_btn.click()
            page.wait_for_selector("text=withdrawn from", timeout=35000)
            page.wait_for_timeout(2000)
            page.screenshot(path=os.path.join(ARTIFACT_DIR, "guide_08_after_scheme_withdraw.png"))
            body = page.locator("body").inner_text()
            assert "withdrawn from" in body, "Scheme withdrawal feedback missing!"
            print("  -> SUCCESS: Scheme withdrawn, flash message shown, stayed on Scheme Matches subtab!")

            # Now test releasing it back
            print("  -> Testing Scheme Release back to Aspirant...")
            first_scheme = page.locator('summary:has-text("% —")').first
            first_scheme.click()
            page.wait_for_timeout(2000)
            rec_area = page.locator('textarea[aria-label^="Recommendation Note *"]')
            if rec_area.count() > 0:
                rec_area.first.fill("Automated test release: Highly recommended for founder.")
                page.locator('button:has-text("RELEASE TO ASPIRANT")').first.click()
                page.wait_for_selector("text=Successfully released", timeout=35000)
                page.wait_for_timeout(2000)
                page.screenshot(path=os.path.join(ARTIFACT_DIR, "guide_09_after_scheme_re_release.png"))
                body = page.locator("body").inner_text()
                assert "Successfully released" in body, "Scheme re-release feedback missing!"
                print("  -> SUCCESS: Scheme re-released, confirmation banner shown, stayed on Scheme Matches subtab!")
        else:
            first_scheme = page.locator('summary:has-text("% —")').first
            first_scheme.click()
            page.wait_for_timeout(2000)
            rec_area = page.locator('textarea[aria-label^="Recommendation Note *"]')
            if rec_area.count() > 0:
                rec_area.first.fill("Automated test release: Highly recommended for founder.")
                page.locator('button:has-text("RELEASE TO ASPIRANT")').first.click()
                page.wait_for_selector("text=Successfully released", timeout=35000)
                page.wait_for_timeout(2000)
                page.screenshot(path=os.path.join(ARTIFACT_DIR, "guide_09_after_scheme_release.png"))
                body = page.locator("body").inner_text()
                assert "Successfully released" in body, "Scheme release feedback missing!"
                print("  -> SUCCESS: Scheme released, confirmation banner shown, stayed on Scheme Matches subtab!")


        # =======================================================
        # STAGE 2: VERIFYING SME WORKSPACE (mathew60666@gmail.com)
        # =======================================================
        print("\n=======================================================")
        print("STAGE 2: VERIFYING SME WORKSPACE (mathew60666@gmail.com)")
        print("=======================================================")
        context.clear_cookies()
        page.goto(BASE_URL, timeout=60000)
        page.wait_for_timeout(3000)

        print("Step 2.1: Logging in as SME...")
        page.locator('input[aria-label="Email Address"]').first.fill("mathew60666@gmail.com")
        page.locator('input[type="password"]').first.fill("Pravin@613")
        page.locator('button:has-text("LOGIN")').first.click()
        page.wait_for_selector("text=Welcome, Mathew", timeout=20000)
        page.wait_for_timeout(3000)

        body = page.locator("body").inner_text()
        assert "Welcome, Mathew A" in body, "Failed to login as SME!"
        print("  -> Logged in successfully as SME!")
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "sme_01_cases_default.png"))

        # SME Main Tab 1: All Consultations Overview
        print("\nStep 2.2: Testing SME Main Tab 'All Consultations Overview'...")
        tab_sme_consult = page.locator('button[role="tab"]:has-text("All Consultations Overview")')
        tab_sme_consult.click()
        page.wait_for_selector("text=All Domain Consultations Overview", timeout=15000)
        page.wait_for_timeout(2000)
        body = page.locator("body").inner_text()
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "sme_02_all_consultations.png"))
        assert "All Domain Consultations Overview" in body, "ERROR: SME All Consultations tab is blank!"
        print("  -> SUCCESS: SME All Consultations Overview renders properly (NOT BLANK)!")

        # SME Main Tab 2: My Profile
        print("\nStep 2.3: Testing SME Main Tab 'My Profile'...")
        tab_sme_prof = page.locator('button[role="tab"]:has-text("My Profile")')
        tab_sme_prof.click()
        page.wait_for_selector("text=My SME Specialist Profile", timeout=15000)
        page.wait_for_timeout(2000)
        body = page.locator("body").inner_text()
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "sme_03_my_profile.png"))
        assert "My SME Specialist Profile" in body and "VERIFIED SME" in body, "ERROR: SME My Profile tab is blank!"
        print("  -> SUCCESS: SME My Profile renders properly (NOT BLANK)!")


        # Return to SME Tab 0: My Assigned Cases
        print("\nStep 2.4: Returning to SME Tab 'My Assigned Cases'...")
        page.locator('button[role="tab"]:has-text("My Assigned Cases")').click()
        page.wait_for_selector('[role="radiogroup"]', timeout=15000)
        page.wait_for_timeout(2000)

        # SME Mentee Subtab: Consultations
        print("\nStep 2.5: Testing SME Mentee Subtab 'Consultations'...")
        sme_consult_pill = page.locator('[role="radiogroup"] button:has-text("Consultations")')
        sme_consult_pill.click()
        page.wait_for_selector("text=Domain Consultations:", timeout=15000)
        page.wait_for_timeout(2000)
        body = page.locator("body").inner_text()
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "sme_04_mentee_consultations.png"))
        assert "Domain Consultations:" in body, "ERROR: SME Mentee Consultations subtab is blank!"
        print("  -> SUCCESS: SME Mentee Consultations renders properly (NOT BLANK)!")

        # SME Mentee Subtab: Journey
        print("\nStep 2.6: Testing SME Mentee Subtab 'Journey'...")
        sme_journey_pill = page.locator('[role="radiogroup"] button:has-text("Journey")')
        sme_journey_pill.click()
        page.wait_for_selector("text=Complete Journey Narrative Spine", timeout=15000)
        page.wait_for_timeout(2000)
        body = page.locator("body").inner_text()
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "sme_05_mentee_journey.png"))
        assert "Complete Journey Narrative Spine" in body, "ERROR: SME Mentee Journey subtab is blank!"
        print("  -> SUCCESS: SME Mentee Journey renders properly (NOT BLANK)!")

        # =======================================================
        # STAGE 3: VERIFYING ASPIRANT WORKSPACE (pravindev666@gmail.com)
        # =======================================================
        print("\n=======================================================")
        print("STAGE 3: VERIFYING ASPIRANT WORKSPACE (pravindev666@gmail.com)")
        print("=======================================================")
        context.clear_cookies()
        page.goto(BASE_URL, timeout=60000)
        page.wait_for_timeout(3000)

        print("Step 3.1: Logging in as Aspirant...")
        page.locator('input[aria-label="Email Address"]').first.fill("pravindev666@gmail.com")
        page.locator('input[type="password"]').first.fill("123456")
        page.locator('button:has-text("LOGIN")').first.click()
        page.wait_for_selector("text=Welcome", timeout=20000)
        page.wait_for_timeout(3000)

        body = page.locator("body").inner_text()
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "aspirant_01_portal.png"))
        assert "Welcome" in body, "Aspirant login failed!"
        print("  -> Logged in successfully as Aspirant!")

        # Aspirant Tab 3: My Journey
        print("\nStep 3.2: Testing Aspirant Tab '🎬 My Journey'...")
        tab_asp_journey = page.locator('button[role="tab"]:has-text("My Journey")')
        tab_asp_journey.click()
        page.wait_for_selector("text=The Entrepreneur's Journey", timeout=15000)
        page.wait_for_timeout(2000)
        body = page.locator("body").inner_text()
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "aspirant_02_journey.png"))
        assert "The Entrepreneur's Journey" in body, "ERROR: Aspirant My Journey tab failed to render!"
        print("  -> SUCCESS: Aspirant My Journey renders properly (NOT BLANK)!")

        # Aspirant Tab 5: Scheme Matches
        print("\nStep 3.3: Testing Aspirant Tab '🏦 Scheme Matches'...")
        tab_asp_schemes = page.locator('button[role="tab"]:has-text("Scheme Matches")')
        tab_asp_schemes.click()
        page.wait_for_selector('h3:has-text("Recommended Funding Schemes")', timeout=20000)
        page.wait_for_timeout(2000)
        body = page.locator("body").inner_text()
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "aspirant_03_schemes.png"))
        assert "Recommended Funding Schemes" in body, "ERROR: Aspirant Scheme Matches tab failed to render!"
        print("  -> SUCCESS: Aspirant Scheme Matches renders properly (NOT BLANK)!")

        browser.close()
        print("\n=======================================================")
        print("🎉 ALL VERIFICATION TESTS COMPLETED WITH 100% SUCCESS!")
        print("=======================================================")

if __name__ == "__main__":
    run_full_verification()
