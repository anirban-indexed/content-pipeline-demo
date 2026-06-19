# BRIEF OUTPUT FORMAT — INSPECTMIND AI

The correct brief format depends on Content Type. Read the content type from the brief data and apply the matching template below.

---

## CONTENT TYPE DISPATCHER — READ THIS FIRST

**DISPATCH PRIORITY — NON-NEGOTIABLE:**

The Content Type field from the CONTENT PLAN CONTEXT block is the **authoritative dispatch signal**. It always overrides URL pattern matching.

- If Content Type is **"Pillar"** or **"Supporting"** → use **Net-New Article** template. Period. Even if the first Target URL is `/checkers/*` or `/compare/*`. Those URLs are internal link destinations within the article — they are NOT the article's own URL.
- If Content Type is **"Landing Page"** or **"Checker"** → use **Checker / Landing Page** template.
- If Content Type is **"Compare"** → use **Compare Page** template.
- If Content Type is **"Optimization"** → use **Optimization** template.
- Only fall back to URL pattern matching if no Content Type is specified.

The Target URLs field in the content plan contains the internal links to place within the article, not the article's own destination URL. Do not use the first Target URL to determine content type. Read the Content Type field.

Before writing a brief, confirm the content type using this table. The content types are fundamentally different and must never be mixed.

| Content Type | URL Pattern | External Links | Internal Links | Pricing Section | Competitor Description |
|---|---|---|---|---|---|
| Net-New Article (Pillar/Supporting) | /education/*, /resources/articles/*, /use-cases/*, /checkers/shop-drawing, etc. | Required (min. 1) | Required (min. 3) | No | No |
| Checker / Landing Page | /checkers/* | PROHIBITED | Required (min. 3) | Yes | No |
| Compare Page | /compare/* | PROHIBITED | Required (min. 3) | Yes (brief) | Yes |
| Optimization | Any existing URL | Depends on original type | Depends on original type | Depends on original type | No |

**Key distinctions:**
- Net-new articles are educational content. They require external citations for credibility and internal links for cluster equity. They do not have a pricing section and do not describe competitors. A net-new article with zero external links is an incomplete brief.
- Compare pages are decision-stage content. They never contain external links — including links to the competitor's own website. They describe the competitor's product, access model, and primary audience — nothing else. No investor names, customer names, or founder names for competitors.
- Checker pages are conversion pages. No external links. The product is the content.

Using the wrong template produces structurally incorrect output. If the URL is /compare/*, use only the Compare Page template. If the URL is /education/* or /resources/articles/*, use only the Net-New Article template.

---

## CONTENT TYPE: NET-NEW ARTICLE (Pillar or Supporting)

Use this format when Content Type is "Pillar", "Supporting", or "Informational" and the page does not yet exist.

---

## INSPECTMIND AI CONTENT BRIEF — [Article Title]

**URL:** [Target URL — first URL from Target URLs field, or TBD if not specified]
**Primary Keyword:** [Primary KW] ([search volume] vol)
**Secondary Keywords:** [comma-separated list from Secondary KWs field]
**Target ICP:** [derive from Product/cluster context and Sub Intent — e.g., "GC / Architect / Engineer" or "Owner / Developer"]
**Target Word Count:** [1,200–1,800 for Supporting | 1,800–2,400 for Pillar]
**Funnel Stage:** [TOFU / MOFU / BOFU]
**Content Type:** [Pillar / Supporting]
**Product/Cluster:** [from Product column]

---

**TITLE TAG:** [Content portion must be 46 characters or fewer — the CMS appends " | InspectMind" automatically. Do not write the "| InspectMind" suffix. Include primary keyword.]
**META DESCRIPTION:** [145–155 characters maximum — lead with the core claim or problem this article addresses, include primary keyword, written for click-through. No em dashes. The description must accurately reflect the article's actual argument.]

---

**STRATEGIC CONTEXT**

[3–4 sentences: why this article exists, what SERP gap it fills, what competitor angle InspectMind's piece must own, and what makes this topic specifically relevant to InspectMind's audience. Draw from the Notes/strategy notes field in the content plan. Mention any existing InspectMind pages this must not duplicate.]

**INTERNAL LINKS TO PLACE**

[List each anchor → target URL pairing, drawn from Target URLs field and the internal link pool. Minimum 3 links required — a net-new article with fewer than 3 internal links is incomplete. Maximum 6. Use natural anchor text that fits within prose. Anchor text must never be a competitor brand name. Anchor text must not begin with a blank or invisible character.

**Pillar articles must link to every supporting article in the same cluster.** If a supporting article does not yet have a live URL, add a placeholder entry in the format: [INTERNAL LINK PLACEHOLDER] Anchor: "[anchor text]" → [Article Title] — add URL once live. Do not skip cluster siblings just because their URL is not yet confirmed.

**Supporting articles must always link to their cluster pillar.** If the pillar URL is live, use it. If not yet live, add a placeholder comment as above.]

- "[anchor text]" → [full URL]
- "[anchor text]" → [full URL]

**EXTERNAL LINKS TO PLACE**

[List 1–2 specific external sources this article should cite. All sources must be from the InspectMind-approved source list: CII, HKA, FMI/PlanGrid, WBDG, ASCE, NIBS, NFPA, ASHRAE, AIA, published AHJ data, or InspectMind's own case study library. Anchor text must identify the specific claim being cited — not a vague "research shows" anchor. Minimum 1 external link is required for every net-new article. A net-new article with zero external links is an incomplete brief.]

- "[specific claim anchor text]" → [full URL or UNCONFIRMED]

**DO NOT DUPLICATE:** [List existing InspectMind URLs whose content this article must not restate. Link to them instead.]

---

**HIGH IMPACT NOTES**

For each H1 and each major H2/H3, provide specific writing instructions. Instructions must be concrete — name what to cover, what specific failure modes or data to reference, what to avoid, and any sourcing requirements. Minimum 2 sentences per heading.

**H1 — [Exact recommended H1 title]**
[Opening instructions: what the first paragraph must establish, what the reader's context is, what must NOT appear as the opening sentence. Always note: do not open with "In this guide/article..." — first sentence must be a direct substantive statement about the problem or mechanism. Do not use the word "streamline."]

**H2 — [Heading]**
[Specific writing instructions: what this section covers, what specific data/failure modes/case study angles to include, any structural gap this fills vs competitors, any sourcing instructions.]

  **H3 — [Subheading]** — [specific instruction for this subheading]

  **H3 — [Subheading]** — [specific instruction]

[Continue per H2/H3 for all major sections...]

**H2 — How InspectMind [Verb + Specific Action Tied to This Article Topic]**
[Instructions for the product section — appears at end of body, before FAQ. 100–120 words maximum. No hard sell. Frame around what InspectMind does in the specific context of this article's topic. Link to the most relevant checker or use-case page. No mid-article product placement — this section always closes the body.]

**H2 — Frequently Asked Questions**
[List specific FAQ questions to answer. Each answer: direct answer first (1 sentence), context second (2–3 sentences). Maximum 4 sentences per answer. Minimum 4 questions, maximum 6.]

- [Question one]
- [Question two]
- [Question three]
- [Question four]

---

## CONTENT TYPE: CHECKER / LANDING PAGE

Use this format when Content Type is "Landing Page" and the URL is at /checkers/*.

---

## INSPECTMIND AI CONTENT BRIEF — [Page Title]

**URL:** [Target URL]
**Primary Keyword:** [Primary KW] ([search volume] vol)
**Secondary Keywords:** [list]
**Target ICP:** [from product context]
**Target Word Count:** 900–1,200 words
**Funnel Stage:** MOFU/BOFU
**⚠ NO EXTERNAL LINKS** — Checker page. All link equity stays on-site. Internal links only. No citation to standards bodies, competitor pages, or third-party sites. Every claim must stand on its own or reference InspectMind's own case studies.

---

**TITLE TAG:** [Content portion must be 46 characters or fewer — the CMS appends " | InspectMind" automatically, bringing the total to 60. Include primary keyword. Do not write the "| InspectMind" suffix yourself.]
**META DESCRIPTION:** [145–155 characters maximum — lead with what AI reviews, include primary keyword, end with "from $50". No em dashes.]

---

**FULL OUTLINE**

**H1 — [Exact H1]**
[Opening instructions. The H1 must signal this is a software solution. The first sentence after H1 must name the problem the reader is trying to solve — NOT a definition. The reader is already in evaluation mode. No definitions of what [discipline] drawing review is. Start with the consequence of not reviewing properly, then pivot to what InspectMind does.]

**H2 — What [Discipline/Check Type] Review Misses Without AI**
[Instructions: establish the specific, concrete failure modes that manual review consistently misses for this discipline. Name the failure modes specifically. Cite sourced cost data if available — flag to editor if no source found. Do not use round-number claims without a named source. Write as prose, not bullets.]

  **H3 — [Specific failure mode or consequence category]** — [instruction]
  **H3 — [Where issues originate in the drawing set]** — [instruction]

**H2 — What the AI [Checker Name] Reviews**
[Instructions: replace bullet feature lists with prose H3s. Each H3 describes what InspectMind actually does, what specific patterns it flags, and why that matters to the ICP. Specific is credible. Do NOT write generic category labels — write the actual failure modes. 2–3 sentences per H3.]

  **H3 — [First specific capability]** — [write what it checks and what a finding looks like]
  **H3 — [Second specific capability]** — [instruction]
  **H3 — [Third specific capability]** — [instruction]
  **H3 — [Fourth specific capability if applicable]** — [instruction]

**H2 — How It Works**
[Three H3s: Upload, Review, Results. Two to three sentences each. Upload: what file types, what to include. Review: what the AI does simultaneously. Results: what the report looks like — sheet reference, detail number, code citation, turnaround time. Keep it tight. Turnaround time must be stated.]

  **H3 — Upload** — PDF drawing set including all discipline sheets and specifications. No CAD or BIM model required.
  **H3 — Review** — AI processes full document set simultaneously across disciplines.
  **H3 — Results** — Flagged issue report with sheet reference, code citation, turnaround.

**H2 — Pricing**
[One short paragraph. From $50 per upload. No per-user fees. Invoice for enterprise. Issue guarantee: 5+ issues or full refund. Then CTA sentence linking to /get-started or /pricing.]

**H2 — Frequently Asked Questions**
[List 4–6 FAQ questions. Include disambiguation questions relevant to this specific checker's SERP context. Each answer: direct first, context second. 3–4 sentences max.]

- [Question 1]
- [Question 2]
- [Question 3]
- [Question 4]

---

## CONTENT TYPE: COMPARE PAGE

Use this format when Content Type is "Supporting" or "Compare" and the URL is at /compare/*.

---

## INSPECTMIND AI CONTENT BRIEF — [Page Title]

**URL:** [Target URL]
**Primary Keyword:** [Competitor name or comparison phrase] ([search volume] vol)
**Target ICP:** AEC professional evaluating [Competitor] vs alternatives
**Target Word Count:** 800–1,100 words
**Funnel Stage:** BOFU
**⚠ NO EXTERNAL LINKS** — Compare page. Do not link to the competitor's website. Do not link to any third-party site. No links to AHJ portals, government databases, or standards bodies. Internal links only. Exception: if the competitor has been publicly acquired, a single factual attribution citation is acceptable — flag this case to the editor before publishing.

---

**TITLE TAG:** InspectMind vs [Competitor]: [1–3 word differentiator]
*(Do not write "| InspectMind" — the CMS appends this automatically. The content portion you write must be 46 characters or fewer so the total rendered title stays at 60 characters or fewer.)*
**META DESCRIPTION:** [145–155 characters maximum — state the core differentiation in a single declarative sentence, include both brand names. No em dashes. The description must accurately reflect the article's primary argument — not a secondary feature.]

---

**COMPETITOR DESCRIPTION GUARDRAILS**

The "What [Competitor] Does" section must follow these constraints:
- Describe what the product does, what access model it uses (demo-gated, self-serve, enterprise-only), and who the primary audience is. Nothing else.
- Do NOT name the competitor's investors, funding rounds, named customers, client logos, or founders.
- Do NOT describe the competitor as "AI-powered", "intelligent", "smart", or any positive technology descriptor. Describe mechanism, not claims.
- Do NOT volunteer capabilities, integrations, or features that InspectMind does not directly address or exceed in the same article. Do not give the competitor a longer feature list than InspectMind gets.
- All competitor facts must be verifiable from their current public website. Flag anything uncertain as [VERIFY: claim] inline. Do not publish editorial notes as body text — the [VERIFY: claim] flag must be resolved before publication.
- Check the competitor's live site for the latest product status, pricing, and access model before writing. Outdated descriptions (wrong turnaround, discontinued features, acquisition not noted) are factual errors.

---

**INTERNAL LINKS TO PLACE**

[List 3–5 internal link pairings. Minimum 3 required — a compare page with fewer is incomplete. Anchor text must describe the InspectMind capability or page — never the competitor's product name. No blank or invisible characters before the linked text. Common high-priority links for compare pages:
- "AI plan check" → https://inspectmind.ai/checkers/plan-check
- "spec vs drawing conflicts" → https://inspectmind.ai/checkers/spec-drawing
- "building code compliance review" → https://inspectmind.ai/checkers/building-codes
- "solutions for architects and engineers" → https://inspectmind.ai/solutions/architects-engineers
- "solutions for general contractors" → https://inspectmind.ai/solutions/contractors
Include the above where relevant and natural. Do not force all five into every article.]

- "[anchor text]" → [full URL]
- "[anchor text]" → [full URL]

---

**FULL OUTLINE**

**H1 — InspectMind vs [Competitor]**
[Opening instructions: lead with the key differentiation angle — e.g., acquisition status (if acquired), access model difference, audience mismatch. The opening paragraph must name both products and the core distinction within two sentences. No preamble. If competitor was recently acquired, lead with that context and its implications for buyers evaluating it.]

**H2 — What [Competitor] Does and Who It's Built For**
[Instructions: factual, neutral description using the competitor description guardrails above. Source all claims from their current public website. Flag unverifiable claims as [VERIFY: claim]. Describe product, access model, and primary audience. Stop there — do not add features that work against InspectMind's position.]

**H2 — What InspectMind Does Differently**
[Instructions: three specific differentiators as H3s. Do not make generic claims like "more powerful" — name specific capability differences that matter to the ICP. Access model, review scope, output specificity, and case study proof are the strongest differentiators.]

  **H3 — Self-Serve Access From Day One** — [InspectMind starts immediately. Describe the workflow: upload, pay, receive findings. Contrast with competitor's access model concretely.]
  **H3 — Full Document Set Review** — [Describe cross-discipline review scope specifically. Name the disciplines and what cross-referencing catches.]
  **H3 — [Third differentiator relevant to this specific competitor]** — [e.g., Spec vs Drawing Detection, Public Case Studies, Pricing Transparency, Issue Guarantee]

**H2 — Feature Comparison**
[Table instructions: compare key dimensions that matter to the ICP. Standard rows: Access Model, Primary Audience, Review Scope, Spec vs Drawing Detection, Output Format, Turnaround, Pricing Transparency, Issue Guarantee. Flag uncertain competitor claims as [VERIFY: claim] in the table cell — do not write "Verify before publishing" as plain text. Note acquisition status if applicable. No em dashes in table cells.]

**H2 — Frequently Asked Questions**
[List 4–5 FAQ questions specific to this comparison. Always include: pricing question, "is [competitor] still available?" if acquisition context applies, and a question about which tool is right for a specific ICP. Each answer: direct first, 3–4 sentences max. No editorial notes or verification flags in FAQ answers — resolve them before writing.]

- [Question 1]
- [Question 2]
- [Question 3]
- [Question 4]

---

## CONTENT TYPE: OPTIMIZATION (Existing Page)

Use this format when the page already exists and the task is to improve it for rankings or intent coverage.

---

## INSPECTMIND AI CONTENT BRIEF — OPTIMIZATION: [Page Title]

**URL:** [Existing URL]
**Primary Keyword:** [Primary KW] ([search volume] vol)
**Current/Previous Position:** [from content plan GSC data if available]
**Secondary Keywords:** [list]
**Target ICP:** [from content plan]
**Target Word Count:** [existing word count range ± expansion target]
**Funnel Stage:** [stage]
**Goal:** [specific ranking goal — e.g., "Push from pos 4 to pos 1–3" or "Recover dropped rankings"]

**⚠ NOTE ON PAGE ACCESS:** InspectMind is a React SPA. The existing page cannot be scraped. Brief instructions are based on competitor SERP analysis and known topical gaps. Editor must paste current page content into the writing brief before the writer starts.

---

**INTERNAL LINKS TO ADD/UPDATE**

- "[anchor text]" → [full URL]
- "[anchor text]" → [full URL]

**DO NOT DUPLICATE:** [Existing InspectMind URLs whose content must not be restated here]

---

**HIGH IMPACT NOTES**

Provide per-heading instructions covering: what must be added (sections missing from the current page but present on competitor pages), what must be fixed (unsourced stats, thin sections, wrong framing), what must be restructured (sections in wrong order, bullets that should be prose), and what must be cut (off-intent sections, speculative content). Be specific — name the heading and exactly what the change is.

**H1 — [Current/recommended H1]**
[Whether to keep or change H1, and why. Note the construction qualifier pattern if relevant.]

[Per-heading instructions in this format:]

**H2 — [Heading]**
[Status: New section | Keep as-is | Expand | Restructure | Cut]
[Specific instructions: what exists, what's missing, what to add or change. Include any data sourcing notes. Flag any unsourced stat bars on the page that need developer fixes.]

  **H3 — [Subheading]** — [Status and instruction]

**SECTIONS TO CUT OR RESTRUCTURE**
[List any sections that should be removed or moved, and why]

**STAT BAR FIXES (flag to developer)**
[List any component-level stat bars that contain unsourced figures — these need a separate developer fix, not just the article rewrite]
