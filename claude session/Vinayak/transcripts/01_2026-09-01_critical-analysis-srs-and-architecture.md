# 1. Critical analysis, SRS and architecture

**Tool:** Claude Code  
**Date:** 2026-09-01  
**Exchanges:** 2 prompts, 23 replies  
**Working folder:** `-Users-vinayak-Desktop`

The proposal reviewed as product manager and systems architect; produced srs.md and architecture.md.

---

### Prompt · 17:29

do a critical analysis, give suumary and steps innvolved. As a professional product manager, systems design and architect give a legit architecture and SRS document and workflows nd process flows. We want it working fully functional, but not overly complex or clunky, we need clean , lean reliable working deployable soluiton. A marketplace where you choose who you trade with — filtered by the things you already have in common.
Team: Brian (Dongwoo), Jaewon (Jae), Vinayak, Kobe
Columbia students buy and sell constantly: furniture at move-out, appliances, textbooks, winter coats. Today that happens in group chats, where a listing scrolls away within an hour and can never be searched, or on Facebook Marketplace, where you are meeting a stranger with no accountability and haggling in norms you may not share. Neither gives you a way to find the people you would actually be comfortable trading with.
Columbia students, verified by a @columbia.edu email address. Nobody without one can sign in during the pilot. Our sharpest use case is MBA students, who arrive and leave on a fixed two-year cycle, furnish an apartment from scratch, and liquidate it on the way out.
The demand is already proven. The Korean Columbia Association group chat has roughly 1,000 members, and the overwhelming majority of its traffic is people buying and selling from each other — a marketplace that exists today with no infrastructure, running entirely on messages that scroll away within the hour.
That community is not our market. It is our proof that the need is real, and our route to a populated launch. We plan to recruit KCA members as our first sellers and have them post the items they are already trying to sell in the chat, so the platform opens with genuine listings from verified Columbia students instead of an empty page. Once that flywheel is turning, the same mechanism extends to every other circle a Columbia student belongs to.
A marketplace where every user declares four attributes — location, nationality, school, industry — and every listing carries the same four from its seller. Buyers turn those attributes on as filters, so the same pool of listings becomes a different marketplace depending on who you are and what you care about.
The bet: trust in a used-goods trade comes from accountability, not from star ratings. When a seller shares your school and your country, a bad transaction has social consequences and you both already know how the exchange is supposed to go. Karrot (당근마켓) built Korea's largest marketplace on GPS-verified neighborhoods; we are testing whether affiliation does the same job in the US.
1. Affiliation profile — four attributes set once at signup. School is verified by email domain; the rest are self-declared.
2. Filtered browse — toggle any of the four filters on or off. The listing count updates live, so the trade-off between trust and selection is never hidden.
3. Match badges — every internal listing shows what you have in common with the seller (SAME AREA · SAME COUNTRY · SAME SCHOOL).
4. Two-tier feed — internal listings from verified Columbia users sit alongside external listings aggregated from other marketplaces. External items are clearly labeled and link out to their source.
5. Audience selection on posting — the seller chooses which circle sees a listing, with the reach count shown for each option. Offer it to your closest community first; widen it if nobody bites.
6. Overlap-only disclosure — you reveal an attribute to another user only where you already share it. Someone with nothing in common sees nothing about you.
So the platform is populated from day one rather than launching empty, we will collect roughly 50 listings each from three existing marketplaces:
- Facebook Marketplace — local NYC listings, the closest comparison to what we are building.
- Karrot (당근마켓 US) — the model we are adapting; useful for category structure and pricing norms.
- eBay — collected through the official eBay Browse API, which returns structured listing and completed-sale data directly.
From each listing we take title, category, asking price, condition, location, source, and source URL. These appear in the feed marked as external, carry no affiliation badges, and redirect to the original marketplace when clicked — we aggregate and point, we do not host the transaction.
- Listings — title, category, asking price, condition, photos, pickup location, posted date, sold date.
- User profiles — location, nationality, school, industry.
- Interaction events — listing views, filter toggles, click-throughs, messages started, items marked sold.
To seed the internal tier we start where the trade already happens: the Korean Columbia Association community, whose group chat gives us real listings, real prices and real categories on day one. From there the same mechanism extends to any circle a Columbia student belongs to.
Does shared affiliation actually change behavior?
Our two-tier feed gives us a clean natural experiment. Internal listings carry affiliation badges; external ones do not. Same feed, same categories, same price ranges. Comparing engagement and click-through between the two directly tests whether "sense of belonging" is a real transaction driver or just a nice story — and it is the single most important thing we could learn.
How tight can a trust circle be before it stops working?
Every filter a user adds buys trust and costs inventory. We can measure exactly where that curve breaks: how many listings the median member sees at each filter depth, and the minimum community size for a circle to stay useful. If a circle of 1,000 produces enough inventory, the model works at surprisingly small scale — and that finding generalizes to every other affiliation group, on this campus and beyond it.
Which of the four filters is doing the work?
Which filters do users keep on, and which do they drop first when their feed runs thin? We expect location and nationality to dominate and industry to go nearly unused — but if school turns out to be the binding one, that changes which communities we would launch next.
Is there an in-group discount?
How do asking prices inside a community compare to external listings for the same category and condition? We expect in-community prices to run lower, because people discount for their own. Quantifying that gap, and finding which categories show it most, would be a genuinely novel result.
How big is the moving-season effect?
Listing volume should spike as one cohort liquidates in May and the next arrives in August. Measuring the size and shape of that mismatch tells us whether the academic calendar is a real liquidity engine or just an intuition.
In scope: profiles, filtered browse, the two-tier feed, listing detail, posting with audience selection, the scraped seed catalog, and the analysis above.
Out of scope: payments, shipping, in-app messaging beyond a contact button, real identity verification, ratings, and a mobile app.
Also excluded on purpose: housing and sublets. Filtering rental listings by nationality raises US fair-housing issues that filtering goods does not.

### Claude Code · 17:29

I'll run this as a structured multi-agent effort: parallel deep-dives on critical analysis, architecture, SRS, and process flows — each working from the full brief — then an adversarial critique pass for consistency and over-engineering before I synthesize everything into a polished document your team can share.

### Claude Code · 17:31

The workflow is running — five agents across two phases. While it works, I'll load the design guidance for the final document.

### Claude Code · 17:31

The five-agent workflow is running in the background — four parallel deep-dives (critical analysis, architecture, SRS, process flows) followed by an adversarial critique pass that checks the drafts against each other for contradictions, over-engineering, and research-validity gaps. Design guidance for the final document is loaded.

When the workflow completes, I'll synthesize everything into a single polished document — critical analysis, executive summary, build steps, full SRS, architecture with data model and query design, and rendered process-flow diagrams — and publish it as a private artifact link you can share with Brian, Jae, and Kobe.

### Claude Code · 17:37

All five agents completed. Let me read the full results — the notification only carried the first section.

### Claude Code · 17:37

The critique found 15 real cross-document conflicts. Let me read the architecture, SRS, and workflows drafts so I can resolve every one in the final document.

### Claude Code · 17:42

Part 1 done (summary + critical analysis). Now the delivery plan and full SRS:

### Claude Code · 17:44

Now the architecture section with the system diagram, corrected schema, and the feed query:

### Claude Code · 17:46

Now the final part — process flows, decision log, and research design appendix:

### Claude Code · 17:48

Two cleanups before publishing — the Flow 5 sequence diagram is missing its closing `end`, and the architecture SVG has leftover invisible draft elements:

### Claude Code · 17:48

The file previews in the Browser pane — let me verify the layout before publishing (mermaid will only render once published, since the artifact runtime provides it):

### Claude Code · 17:48

All tags balanced, eight mermaid flows, eight sections, 105 KB. Publishing:

### Claude Code · 17:49

Published. Let me visually verify the rendered artifact — especially the mermaid diagrams:

### Claude Code · 17:49

The document is published — the "page not found" in my preview pane is just the unauthenticated in-app browser; the artifact is private to your account and will open fine from your own signed-in browser or via `/artifacts` in the terminal.

## Done — full analysis, SRS, architecture, and process flows

**📄 [LionsList — the complete document](https://claude.ai/code/artifact/399adab6-26f3-4303-b54d-f339248ae992)** — private to you until you share it with Brian, Jae, and Kobe from the page's share menu.

I ran this as five parallel specialist passes (critical analysis, architecture, SRS, workflows, then an adversarial critique of all four against each other). The critique caught **15 real cross-document conflicts** — including a hard visibility-gating design that contradicted the legal analysis, a missing impression event that would have left Q1's click-through rate with no denominator, and photo uploads that would have shipped students' home GPS coordinates in EXIF data. All 15 are resolved in the final document.

### The verdict in brief

The concept is sound and genuinely well-scoped — but **two things must change before any code is written**:

1. **Drop all Facebook/Karrot scraping.** Both prohibit it, Meta litigates as policy, and FB's login wall pushes exposure toward CFAA territory — a bad trade for ~100 listings that are an afternoon of manual data entry. The seed becomes: eBay Browse API (fully legitimate) + a hand-entered, team-reviewed spreadsheet.
2. **Audience selection promotes, never hides.** Seller-side "only my nationality sees this" reproduces the *Roommates.com* pattern courts have penalized platforms for, and it's one Spectator headline from an administrative problem. The fix: chosen circles see the listing *first and ranked on top*, but every listing stays reachable by all verified users. Every Q2/Q3 data point survives.

**One thing must be added:** Q1 as designed is confounded beyond repair (internal vs external listings differ in photos, price, freshness, and friction — not just badges). The fix costs one boolean: randomize badge visibility per impression, turning Q1 into a real experiment. Q4 also gets reframed (internal-vs-eBay prices measure market structure, not in-group generosity; comparing price against circle tightness *within* internal listings is cleaner and more novel).

### What's in the document

- **Critical analysis** — 6 genuine strengths, 9 ranked risks, a verdict + fix for each research question Q1–Q5
- **Delivery plan** — 5 phases over ~6 weeks for 4 people, each with a demo gate
- **Full SRS** — ~50 numbered, testable requirements, exact overlap-disclosure semantics, the canonical 9-event analytics taxonomy, Given/When/Then acceptance criteria, MoSCoW table
- **Architecture** — one Next.js + Supabase monolith (~$26/month), complete SQL schema, the single feed query that *is* the product (filters + circle boost + privacy-by-projection + badges + live count in one statement), 14 API entry points, seed scripts, deployment
- **8 process flows** — signup, browse, detail, posting, contact handoff, seed ops, disclosure logic, moving-season lifecycle, all as rendered diagrams
- **Decision log** — 6 decisions (D-1 to D-6) written as recommendation-plus-alternative for the team to ratify at kickoff, since several can't be retrofitted after launch
- **Research appendix** — the five SQL views that answer Q1–Q5, with the two non-obvious ones written out

The one non-obvious pre-launch item worth flagging now: file the **IRB determination** (likely exempt, but determined — not assumed) before collecting data, since consent can't be retrofitted.

### Prompt · 17:52

give the document so that I can sahre it and download it

### Claude Code · 17:52

Two deliverables coming up: a self-contained HTML file (with the diagrams embedded so they render anywhere) and a PDF for easy sharing. Building the standalone version first:

### Claude Code · 17:52

Chrome is available. Rendering the PDF (with time budget for the diagrams to draw):

### Claude Code · 17:53

PDF looks excellent — typography and callouts render perfectly, and the section pills double as a clickable TOC. Let me verify the diagrams rendered inside it:

### Claude Code · 17:53

Code and tables render beautifully. Now checking the mermaid flow diagrams near the end:

### Claude Code · 17:54

All 8 diagrams are now static SVG. Let me check their sizing attributes and build the print-ready variant:

### Claude Code · 17:54

Some diagrams were captured mid-render (duplicate IDs, missing viewBox) — the race under virtual time. I'll switch to an explicit sequential `mermaid.run()` that completes before the dump:

### Claude Code · 17:55

Virtual-time still races mermaid's renderer. Switching to the purpose-built tool — mermaid-cli pointed at the system Chrome:

### Claude Code · 17:56

All 8 flows rendered to clean standalone SVGs. Now building the print edition with the diagrams inlined statically, and re-printing the PDF:

### Claude Code · 17:56

Diagrams render perfectly now. Quick final check on the hand-drawn architecture diagram and total page count:

### Claude Code · 17:57

Here's the document in all three forms — pick whichever fits how you want to share it:

**1. 📄 [LionsList-Product-Spec.pdf](LionsList-Product-Spec.pdf)** — 57 pages, all 8 process-flow diagrams rendered, ready to email, print, or drop in a group chat. Also saved to your Desktop.

**2. 🌐 [LionsList-Product-Spec.html](LionsList-Product-Spec.html)** — the same document as a single self-contained web file (diagrams embedded as static SVG, no internet needed). Open it in Safari, host it anywhere, or send it as-is. Also on your Desktop.

**3. 🔗 [The live artifact](https://claude.ai/code/artifact/399adab6-26f3-4303-b54d-f339248ae992)** — for web sharing with Brian, Jae, and Kobe: open it in your browser, click the **share menu on the page itself**, and choose who can view. It stays private until you do that. Teammates get the interactive version with the sticky section navigation, plus light/dark theme support.

One production note from the export: the PDF's diagrams initially broke under print pagination, so I pre-rendered all 8 mermaid flows to static SVG (via mermaid-cli against your installed Chrome) and rebuilt the print edition around them — that's why the flowcharts and the contact-handoff sequence diagram come out crisp on their own pages rather than overlapping.

