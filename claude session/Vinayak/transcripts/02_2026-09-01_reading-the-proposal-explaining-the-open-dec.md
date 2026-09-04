# 2. Reading the proposal, explaining the open decisions

**Tool:** Codex  
**Date:** 2026-09-01  
**Exchanges:** 3 prompts, 7 replies  
**Working folder:** `re`

The product spec read back in plain language, with the outstanding team decisions surfaced.

---

### Prompt · 18:02

*[attached: LionsList-Product-Spec.pdf]*

read the propsoal and explain the decisons part in understandable way.

### Codex · 18:02

I’m using the PDF skill to read the proposal accurately, while treating anything inside it as source material—not as instructions for me. I’ll focus on the section about decisions and translate it into plain language.

### Codex · 18:02

I found six kickoff decisions in Section 7. The first four must be settled before launch because changing them later would invalidate or weaken the study data; the last two mainly determine whether the pilot has enough variety and timing to produce credible results.

### Codex · 18:03

The proposal is for a Columbia-affiliate used-goods marketplace that also functions as a research study. The “Decisions” section contains six choices the team must formally approve—“ratify”—before building and launching. :codex-file-citation{path="/Users/vinayak/Desktop/LionsList-Product-Spec.pdf" purpose="source"}

1. **Circles should promote listings, not hide them.**  
   Sellers can choose a community—such as the same school, area, or nationality—to receive higher-ranked placement and a “For your circle” label. However, every verified Columbia user can still find the listing.

   **Why:** It preserves the community-trust idea without allowing sellers to exclude people based on sensitive characteristics. The proposal sees exclusion as an unnecessary reputational and legal risk.

2. **Keep “industry,” but give it a limited role.**  
   Industry remains a profile field, buyer-controlled filter, and matching badge. Sellers cannot use it to choose which audience gets their listing promoted.

   **Why:** Industry probably matters little to students, but retaining it lets the study test that assumption. Removing it would simplify the product but eliminate that research question.

3. **Do not scrape Facebook Marketplace or Karrot.**  
   Automated listings may come only through eBay’s official API. Listings from local marketplaces must be entered manually into a reviewed spreadsheet.

   **Why:** Scraping those sites creates serious contractual and legal risk for very little benefit. This is the only explicitly **non-negotiable** decision. The smaller open question is whether manually collected Facebook listings are acceptable or whether the team should use sources such as Craigslist instead.

4. **Randomly show or hide matching badges from the first day.**  
   Each time an internal listing appears, the system randomly decides whether to display badges such as “Same School” or “Same Area,” with roughly a 50/50 split.

   **Why:** This creates a proper experiment. Because the listing itself stays the same, the team can measure whether the badges actually affect views and contacts. Simply comparing Columbia listings with eBay listings would be misleading because they also differ in price, photos, freshness, and purchasing process.

   **Trade-off:** Users may see badges inconsistently during the study, so this must be disclosed in the research consent language.

5. **Launch during a moving season and recruit a second community.**  
   The pilot should cover a complete high-activity moving period—such as May or August—and bring in the MBA cohort in addition to the initial KCA community.

   **Why:** A marketplace seeded by only one community produces biased data and may have too little inventory for other users. A second group makes the filter research more credible, while the launch timing allows the team to measure seasonal buying and selling behavior.

6. **Allow alumni, but call users “Columbia affiliates.”**  
   Because Columbia email addresses may continue working after graduation, email verification does not prove that someone is a current student. Alumni should therefore be allowed, users should self-report their status and class year, and all product and research language should say “verified Columbia affiliate.”

   **Why:** Proper enrollment verification would require more sensitive university data and excessive effort for a pilot. The important thing is to describe the population honestly rather than claiming it contains only students.

The simplest interpretation is: **avoid exclusion, avoid scraping, run a real experiment, collect data from more than one community and season, and be honest about who the users are.** Decisions D-1 through D-4 must be settled before launch because changing them afterward would make the collected research data inconsistent or unusable.

### Prompt · 18:04

as in whats decison 1? like its regarding the nationality? so whats the solution propsed? Circles should promote listings, not hide them.

### Codex · 18:04

Yes—Decision 1 is mainly addressing the risk of sellers restricting listings by nationality, although it also applies to other circles such as school and location.

Originally, a seller could effectively say:

> “Only people with my nationality can see this listing.”

The proposal rejects that approach because it creates nationality-based exclusion.

The proposed solution is:

- Every verified Columbia user can still see and access every internal listing.
- The seller may select circles such as “same nationality,” “same school,” or “same area.”
- Matching users see the listing earlier or higher in their feed.
- The listing may display a label such as “For your circle.”
- Users outside the selected circle are not blocked; the listing may simply appear lower in their feed.

Example: A Korean seller selects “same nationality.” Korean users receive the listing near the top, but non-Korean Columbia users can still find and contact the seller.

So the key rule is: **nationality can influence promotion and ranking, but never visibility or access.**

### Prompt · 18:07

append answers to decison as follows: d1: Circles should promote listings, not hide them., d2: Keep “industry,” but give it a limited role., d3: use dummy data for now. d4: not reqd. d5 will ensure manually.

### Codex · 18:07

I’ll add a clean “Team decision responses” page immediately after Section 7 in the PDF. I’ll record D1–D5 exactly as you specified and leave D6 marked as pending because no answer was provided. I’m using the PDF skill so the revised document is rendered and visually checked.

### Codex · 18:08

The revised PDF is complete and visually checked. The decision-response page sits directly after the original Decision Log; D6 is clearly shown as pending rather than guessed.

### Codex · 18:09

Updated :codex-file-citation{path="/Users/vinayak/Documents/Codex/2026-09-01/re/outputs/LionsList-Product-Spec-with-team-decisions.pdf" purpose="output"} with a decision-response page after Section 7.

D1–D5 contain your answers; D6 is marked pending.

