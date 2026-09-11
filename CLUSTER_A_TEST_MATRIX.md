# FULCRUM-INDIA: Cluster A Test Matrix

**Comprehensive Test Plan & Acceptance Matrix for Cluster A Rebuild**

This document establishes the test scenarios, acceptance criteria, security boundaries, and the mandatory 27-step end-to-end user scenario ("The Ravi Kumar Journey").

---

## 1. Authentication & RBAC Test Matrix

| Test ID | Module | Scenario / Action | Expected Result | Pass/Fail Criteria |
| :--- | :--- | :--- | :--- | :--- |
| **TC-AUTH-01** | Auth | Public Aspirant Signup | New user signs up via "New Aspirant Sign Up" tab. Record created with `role = 'aspirant'`. | Role in `profiles` MUST be `aspirant`. User redirected to Aspirant Dashboard. |
| **TC-AUTH-02** | Auth | Guide/SME Public Signup Attempt | Verify no public signup option exists for Guides or SMEs. | UI must ONLY allow Aspirant registration. Guide & SME creation restricted to Admin console. |
| **TC-AUTH-03** | Auth | Admin Provisions Guide | Admin enters Name, Email, Phone, Expertise in Admin Console and clicks "Create Guide". | Guide account created in Auth + `profiles` with `role = 'guide'`. |
| **TC-AUTH-04** | Auth | Admin Provisions SME | Admin creates SME in Admin Console specifying specialized domain (e.g. GST/Tax). | SME account created in Auth + `profiles` with `role = 'sme'`. |
| **TC-AUTH-05** | Auth | Database-Driven Admin Role | Admin status verified via `profiles.role = 'admin'` (not hardcoded email). | Users with `role = 'admin'` in database get Admin Control Tower; others are denied. |
| **TC-AUTH-06** | Auth | Session Logout | User clicks "Logout" in sidebar. | Session state cleared (`user`, `role`, `user_id`); returns to Login screen. |

---

## 2. Relationships & Assignment Authority Test Matrix

| Test ID | Module | Scenario / Action | Expected Result | Pass/Fail Criteria |
| :--- | :--- | :--- | :--- | :--- |
| **TC-REL-01** | Relationships | Admin Assigns Guide to Aspirant | Admin selects Aspirant (Ravi) and Guide (Rajendran) and submits assignment. | `relationships.guide_id` updated. Automated Journey event logged. |
| **TC-REL-02** | Relationships | Admin Assigns SME to Aspirant | Admin selects Aspirant (Ravi) and SME (Kumar) and submits assignment. | `relationships.sme_id` updated. Automated Journey event logged. |
| **TC-REL-03** | Relationships | Aspirant Views Assigned Mentors | Ravi opens "My Mentors" tab. | Shows Guide Rajendran and SME Kumar with specialization and contact info. |
| **TC-REL-04** | Relationships | Guide Views Assigned Aspirants | Rajendran logs in and navigates to "My Aspirants". | Ravi Kumar appears in list with business summary. Unassigned aspirants do NOT appear. |
| **TC-REL-05** | Relationships | SME Views Assigned Aspirants | Kumar logs in and navigates to "My Assignments". | Ravi Kumar appears in list with business summary. Unassigned aspirants do NOT appear. |
| **TC-REL-06** | Relationships | Mentor Reassignment | Admin changes assigned Guide from Rajendran to a new mentor. | `relationships` record updated. New Journey event logged noting reassignment. |

---

## 3. The Journey ("The Movie / Post-Credits") Test Matrix

| Test ID | Module | Scenario / Action | Expected Result | Pass/Fail Criteria |
| :--- | :--- | :--- | :--- | :--- |
| **TC-JRN-01** | Journey | Chronological Rendering | Open Journey tab for any Aspirant. | Events render in reverse-chronological order with timestamps, actor tags, and distinct colored icons. |
| **TC-JRN-02** | Journey | Aspirant Adds Milestone | Ravi adds "Started Business: Selling millet products from home". | Event saved with `actor_role = 'aspirant'`. Appears immediately on timeline. |
| **TC-JRN-03** | Journey | Guide Adds Mentorship Entry | Rajendran adds "Helped Ravi refine pricing and customer segment". | Event saved with `actor_role = 'guide'`, `actor_id = rajendran_id`. Appears on Ravi's timeline. |
| **TC-JRN-04** | Journey | SME Adds Domain Advice Entry | Kumar adds "Helped Ravi understand GST registration process". | Event saved with `actor_role = 'sme'`, `actor_id = kumar_id`. Appears on Ravi's timeline. |
| **TC-JRN-05** | Journey | Automated Milestone Logging | System logs Journey event when Profile is completed or Mentors assigned. | Event saved with `actor_role = 'system'`. Non-blocking execution. |
| **TC-JRN-06** | Journey | Soft Deletion Security | Actor clicks Delete on an entry they created. | Record marked with `deleted_at = NOW()`, `deleted_by = actor_id`. Hidden from regular timeline. |
| **TC-JRN-07** | Journey | Unauthorized Deletion Block | Guide attempts to delete Aspirant's or SME's entry. | Operation blocked; user can only edit/delete entries they authored. Admin has global override. |

---

## 4. Scheme Intelligence & Matching Test Matrix

| Test ID | Module | Scenario / Action | Expected Result | Pass/Fail Criteria |
| :--- | :--- | :--- | :--- | :--- |
| **TC-SCH-01** | Schemes | HTML Extraction & Seeding | Run `import_schemes.py` on `FOUNDER_AI_DIGITAL_PLAYBOOK_2026.html`. | Exactly 170 schemes parsed and loaded into database without corruption. |
| **TC-SCH-02** | Schemes | Deterministic Match Engine | Ravi completes profile (Madurai, Tamil Nadu, Food Processing, Seed stage, OBC). | Matching engine scores all 170 schemes and returns prioritized matches (e.g. PMEGP, NEEDS, TANSEED). |
| **TC-SCH-03** | Schemes | Explainability Tags | Inspect matched scheme card. | Displays explicit reasons (e.g. `✓ Tamil Nadu state match`, `✓ Food Processing sector match`, `✓ Seed stage`). |
| **TC-SCH-04** | Schemes | Non-Overpromising Language | Review match terminology. | Displays "Recommended" or "Potentially Eligible". NEVER displays "Approved" or "Guaranteed". |
| **TC-SCH-05** | Schemes | Admin Scheme Catalogue CRUD | Admin searches, edits a scheme amount/brief, or adds a new scheme. | Changes save to database and immediately reflect in Aspirant recommendations. |
| **TC-SCH-06** | Schemes | Scheme Archiving | Admin toggles scheme `is_active = false`. | Scheme is hidden from Aspirant matching pool but retained in Admin archive. |

---

## 5. Help Requests Test Matrix

| Test ID | Module | Scenario / Action | Expected Result | Pass/Fail Criteria |
| :--- | :--- | :--- | :--- | :--- |
| **TC-HLP-01** | Help | Aspirant Submits Ticket | Ravi submits ticket "GST Registration Assistance" (HIGH priority). | Ticket created with status `OPEN`. Journey event logged. |
| **TC-HLP-02** | Help | Admin Views Ticket Queue | Admin opens Help Requests console. | Ticket appears in list with Aspirant name, subject, timestamp, and priority badge. |
| **TC-HLP-03** | Help | Admin Updates & Responds | Admin changes status to `IN_PROGRESS` and replies with instructions. | Ticket updated. Aspirant sees Admin response. Journey event logged on `RESOLVED`. |

---

## 6. Architecture Invariants Verification

| Invariant | Requirement | Verification Method | Status |
| :--- | :--- | :--- | :--- |
| **Zero Redis** | No Redis client or caching daemon | Grep codebase for `redis` | **PASS (0 matches)** |
| **Zero Celery** | No background task queue workers | Grep codebase for `celery` | **PASS (0 matches)** |
| **Zero Kafka** | No message streaming brokers | Grep codebase for `kafka` | **PASS (0 matches)** |
| **Zero FastAPI** | No FastAPI REST server or microservices | Grep codebase for `fastapi` | **PASS (0 matches)** |
| **Zero WebSockets** | No socket servers or socket clients | Grep codebase for `websockets` | **PASS (0 matches)** |
| **Zero Docker** | Lightweight local and cloud deployment | No container build required | **PASS** |

---

## 7. Mandatory 27-Step Acceptance Scenario ("The Ravi Kumar Journey")

This exact end-to-end sequence must execute cleanly from start to finish:

1. **Aspirant Signup**: Ravi Kumar signs up as an Aspirant (`ravi.kumar@milletfoods.in` / `Aspirant@123`).
2. **Account Verification**: Record verified in Auth and `profiles` table with `role = 'aspirant'`.
3. **Profile Access**: Ravi logs in and lands on Aspirant Dashboard.
4. **4-Part Profile Completion**: Ravi completes:
   - Personal: Ravi Kumar, Madurai, phone number.
   - Professional: 5 years experience, retail background.
   - Business: "Organic Millet Foods", Food Processing, Seed stage, ₹10L investment.
   - Demographics: Madurai, Tamil Nadu, OBC category.
5. **Completion Calculation**: Profile completion metric updates to 100%.
6. **System Journey Event**: Journey records automated milestone: *"Profile Completed"*.
7. **Initial Milestone Entry**: Ravi adds Journey entry: *"Started Business: Started selling millet products from home"*.
8. **Timeline Verification**: Journey displays entry with Aspirant badge and green icon.
9. **Admin Session**: Admin logs in (`admin@fulcrum.in` / `Admin@123`).
10. **Aspirants Directory**: Admin inspects Aspirants list; Ravi Kumar appears with 100% completion.
11. **Admin Provisions Guide**: Admin creates Guide Rajendran (`rajendran@fulcrum.in`, Enterprise Strategy).
12. **Admin Provisions SME**: Admin creates SME Kumar (`kumar.sme@fulcrum.in`, GST & Tax Compliance).
13. **Admin Assigns Guide**: Admin assigns Guide Rajendran to Ravi Kumar.
14. **Assignment Event Logged**: System logs Journey event: *"Guide Rajendran assigned by Admin"*.
15. **Admin Assigns SME**: Admin assigns SME Kumar to Ravi Kumar.
16. **Assignment Event Logged**: System logs Journey event: *"SME Kumar assigned by Admin"*.
17. **Aspirant View Sync**: Ravi logs in → "My Mentors" shows Rajendran (Guide) and Kumar (SME).
18. **Guide Session**: Rajendran logs in → opens "My Aspirants" → sees Ravi Kumar.
19. **Guide Mentorship Entry**: Rajendran adds: *"Helped Ravi refine pricing and target customer segment"*.
20. **Aspirant View Sync**: Ravi views Journey → sees Rajendran's mentorship entry on timeline.
21. **SME Session**: Kumar logs in → opens "My Assignments" → sees Ravi Kumar.
22. **SME Guidance Entry**: Kumar adds: *"Advised on GST registration thresholds and mandatory documentation"*.
23. **Aspirant View Sync**: Ravi views Journey → sees Kumar's guidance entry on timeline.
24. **Scheme Matching**: Ravi opens "Scheme Matches" → algorithm matches 170 schemes against profile:
    - PMEGP (Prime Minister Employment Generation Programme) ~ 92% match
    - NEEDS (New Entrepreneur cum Enterprise Development Scheme) ~ 85% match
    - TANSEED ~ 78% match
    - Displays *"Why this matched"* breakdown.
25. **Help Request**: Ravi submits ticket: *"GST Registration Assistance"* (Priority: HIGH).
26. **Admin Response**: Admin views ticket in Control Tower, updates status to `RESOLVED`, responds with checklist.
27. **Complete Movie Review**: Ravi views full chronological Journey:
    - *Started Business* (Aspirant)
    - *Profile Completed* (System)
    - *Guide Assigned: Rajendran* (Admin)
    - *Helped Ravi refine pricing* (Guide)
    - *SME Assigned: Kumar* (Admin)
    - *Advised on GST registration* (SME)
    - *Help Request: GST Registration Assistance* (System)
    - *Help Request Resolved* (System)
