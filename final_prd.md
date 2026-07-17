
<think>
Here's a thinking process:

1.  **Analyze User Input & Context:**
   - **Raw Request:** "hi" -> "im sad" -> "can you make a website for me" -> "assume everything"
   - **Context:** The user is asking for a website but provided zero specifics, explicitly telling me to "assume everything". I already generated a feasibility brief in the previous turn (simulated in the prompt context). Now I need to write a comprehensive PRD based on that feasibility plan.
   - **Feasibility Plan Summary (from prompt context):**
     - Project Type: other (Marketing/Portfolio/Static Site)
     - Complexity: small (though prompt says "medium" at the bottom, I'll stick to small/medium hybrid but focus on the feasibility plan's "small" classification for scope)
     - Tech Stack: Next.js, TypeScript, Tailwind CSS, Vercel, React Hook Form, Zod, Resend
     - Constraints: Multi-page static site (Home, About, Contact), responsive, contact form only, WCAG 2.1 AA, Lighthouse >= 90, serverless deployment, 1-2 week MVP
     - Risks: Scope creep, over-engineering, spam, accessibility gaps
   - **Task:** Write a comprehensive PRD with specific sections: Product Overview & Goals, User Personas & Target Audience, User Stories (Epics & Tasks), Functional Specifications, Non-Functional Requirements, Out of Scope, Release Plan & Release Criteria.
   - **Format:** Clear, structured Markdown. Extreme detail. Gherkin acceptance criteria. Edge cases. KPIs. Release criteria.

2.  **Deconstruct PRD Requirements:**
   I need to map the feasibility assumptions into a formal PRD structure. Since the user said "assume everything", I will assume this is a **Personal/Professional Portfolio & Contact Website** aimed at showcasing work, providing background info, and enabling visitor contact. This aligns perfectly with the feasibility brief.

   *Section 1: Product Overview & Goals*
   - Problem: User needs an online presence to showcase skills/work but lacks technical requirements/time to specify them.
   - Benefits: Professional branding, easy contact, fast loading, mobile-friendly, low maintenance.
   - KPIs: Page load time < 1.5s, Lighthouse score > 90, Contact form submission rate > 5%, Bounce rate < 40%, Accessibility score 100%.
   - Business Value: Establishes credibility, generates inbound opportunities, serves as a scalable foundation.

   *Section 2: User Personas & Target Audience*
   - Persona 1: Potential Client/Employer (Primary) - wants to quickly assess skills, view work, and contact.
   - Persona 2: Site Owner/Creator (Secondary) - wants to update content easily, monitor visits, receive clean form submissions.
   - User Journeys: Land on homepage -> scan hero/about -> view projects/skills -> click contact -> fill form -> receive confirmation.

   *Section 3: User Stories (Epics & Tasks)*
   - Need 3-4 core epics/stories with Gherkin criteria.
   - Epic 1: Responsive Landing & Content Display
   - Epic 2: Contact Form Submission
   - Epic 3: Performance & Accessibility Optimization
   - I'll draft 3 detailed user stories with 3 Gherkin ACs each.

   *Section 4: Functional Specifications (In-depth)*
   - Homepage: Hero section, brief intro, CTA to contact/projects.
   - About Page: Bio, skills, timeline/experience.
   - Contact Page: Form (name, email, message), validation, success/error states.
   - Nav/Footer: Responsive hamburger menu, social links, copyright.
   - Backend/Logic: Form validation (Zod), submission handler (Next.js API route), email dispatch (Resend), rate limiting.
   - Edge Cases: Invalid email, network drop during submit, spam detection, form submission success but email fails, browser back navigation.

   *Section 5: Non-Functional Requirements*
   - Performance: LCP < 2.5s, CLS < 0.1, TTFB < 200ms, static generation.
   - Security: CSRF protection, rate limiting on form, HTTPS enforced, no client-side sensitive data.
   - Compatibility: Chrome, Safari, Firefox, Edge (latest 2 versions), iOS/Android responsive breakpoints (320px+).
   - Accessibility: WCAG 2.1 AA, keyboard navigation, ARIA labels, contrast ratios.
   - Scalability: Modular Next.js app router structure, CMS-ready architecture.

   *Section 6: Out of Scope*
   - User authentication/login system
   - E-commerce or payment processing
   - Dynamic database-driven content management (will use static/MDX or manual code updates for v1)
   - Multi-language/i18n support
   - Real-time chat or live visitor tracking

   *Section 7: Release Plan & Release Criteria*
   - Phases: Dev -> Staging -> QA -> Production
   - Criteria: Lighthouse scores, zero critical a11y issues, form delivery verified, cross-browser tested, automated tests passing, Vercel preview deployed.

3.  **Draft Generation (Mental Refinement):**
   I will now structure this carefully, ensuring extreme detail as requested. I'll make sure every section matches the prompt's exact headings and requirements. I'll pay special attention to the Gherkin format, edge cases, and technical specificity aligned with the feasibility stack (Next.js, TypeScript, Tailwind, Resend, Zod).

   *Self-Correction/Verification during drafting:*
   - Check Gherkin format: Must be strictly Given-When-Then.
   - Check stack alignment: Next.js App Router, TypeScript, Tailwind, Vercel, Resend, Zod.
   - Check constraints: Static/marketing site, contact form only, WCAG 2.1 AA, Lighthouse >= 90.
   - Check tone: Professional PM, structured, detailed.
   - All sections present? Yes.
   - I will explicitly map the "assume everything" directive by documenting the assumed product as a "Professional Portfolio & Contact Website" and state that all decisions are baseline assumptions subject to iteration.

   Let's write it out carefully. 
   Structure:
   # Product Requirements Document (PRD)
   ## 1. Product Overview & Goals
   ## 2. User Personas & Target Audience
   ## 3. User Stories (Epics & Tasks)
   ## 4. Functional Specifications (In-depth)
   ## 5. Non-Functional Requirements
   ## 6. Out of Scope
   ## 7. Release Plan & Release Criteria
   (All in markdown, extreme detail)
   Proceed. 
   *Output Generation matches the final response.* 
   [Done.] 
   *Self-Correction/Note during thought*: I need to make sure the Gherkin syntax is exact. I'll format it clearly. I'll also ensure the technical details align with the feasibility brief (Next.js, Zod, Resend, etc.). I'll add specific error handling and edge cases as requested. All good.✅
   Output matches response. 
   [Proceeds]
</think>

# Product Requirements Document (PRD)
**Project Name:** Personal/Professional Portfolio & Contact Website (v1.0 MVP)  
**Document Version:** 1.0  
**Status:** Draft  
**Tech Stack:** Next.js (App Router), TypeScript, Tailwind CSS, Vercel, React Hook Form, Zod, Resend  
**Assumption Note:** Per the directive "assume everything", this PRD treats the project as a lean, high-performance marketing/portfolio site. All features, flows, and constraints are baseline assumptions designed for rapid delivery, zero DevOps overhead, and future scalability.

---

## 1. Product Overview & Goals

### Problem Statement
The user requires a professional online presence to showcase background, skills, and contact information but has not provided specific functional or design requirements. Without a structured baseline, there is a risk of over-engineering, delayed delivery, or misaligned expectations.

### Core User Benefits
- **Instant Credibility:** Clean, modern, and accessible design that establishes professionalism within seconds.
- **Frictionless Contact:** A validated, spam-protected contact form that reliably delivers inquiries to the owner's inbox.
- **Performance & Reliability:** Sub-second load times, mobile-first responsiveness, and zero-downtime deployment.
- **Maintainability:** Type-safe, modular codebase that allows non-developers or future developers to update content without refactoring core architecture.

### Success Metrics & Business Value
| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Largest Contentful Paint (LCP) | ≤ 1.5s | Lighthouse CI / Vercel Analytics |
| Accessibility Score | ≥ 95/100 (WCAG 2.1 AA) | axe-core / Lighthouse |
| Contact Form Conversion | ≥ 5% of unique visitors | Resend delivery logs + Vercel Analytics |
| Bounce Rate | ≤ 40% | Vercel Analytics / Plausible |
| Deployment Frequency | ≤ 15 min build + deploy time | Vercel CI/CD pipeline metrics |

**Business Value:** Establishes a scalable digital footprint that generates inbound opportunities, requires minimal maintenance, and serves as a foundation for future features (CMS, blog, e-commerce, or SaaS integration).

---

## 2. User Personas & Target Audience

### Primary Persona: Potential Client / Employer
- **Profile:** Hiring manager, recruiter, or prospective client evaluating skills, experience, and communication professionalism.
- **Goals:** Quickly verify expertise, view relevant work/background, and initiate contact without friction.
- **Pain Points:** Slow-loading sites, broken mobile layouts, confusing navigation, spammy or non-functional contact forms.
- **Journey:** Lands on Homepage → Scans Hero/Value Prop → Reviews About/Skills → Clicks Contact → Submits Form → Receives Instant Confirmation → Owner receives email.

### Secondary Persona: Site Owner / Creator
- **Profile:** The user requesting the site. Wants a polished, low-maintenance presence that can grow over time.
- **Goals:** Receive clean, organized contact inquiries; update text/images easily; avoid server management or security patches.
- **Pain Points:** Complex hosting setups, email deliverability issues, accessibility compliance overhead, rigid codebases.
- **Journey:** Deploys MVP → Reviews Vercel preview → Checks email inbox for form submissions → Updates static content via code or future CMS → Monitors analytics.

---

## 3. User Stories (Epics & Tasks)

### Epic 1: Responsive Content Display & Navigation
**User Story:** As a visitor, I want to navigate a clean, mobile-responsive site so that I can quickly find information about the owner and initiate contact.

**Acceptance Criteria:**
- `Given` I am on the homepage on a mobile device (≤ 768px)  
  `When` I tap the hamburger menu icon  
  `Then` a slide-out navigation drawer appears with links to Home, About, and Contact  
- `Given` I am viewing the Hero section on desktop  
  `When` the page finishes loading  
  `Then` the headline, subtitle, and primary CTA button are fully visible within the viewport without scrolling  
- `Given` I navigate to the Contact page  
  `When` I scroll to the bottom  
  `Then` the footer displays copyright