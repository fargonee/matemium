# Matemium Legal Documentation

This document summarizes all legal and policy materials for the Matemium project (desktop application + website + cloud services).

## Core Policies (Published on Website)

These pages are implemented as React routes in the marketing/dashboard website:

- **Privacy Policy** — `/privacy`
  - Data collection (Supabase auth, Lemon Squeezy billing, LLM proxy context)
  - Local-only rendering (no media uploaded)
  - Third parties: Supabase, Lemon Squeezy, LLM providers
  - User rights and data retention

- **Terms of Service** — `/terms`
  - Account rules
  - Subscription model and licensing by plan (Free / Pro / Teams)
  - User content ownership + limited license grant for AI processing
  - AI disclaimers (assistive only)
  - Broad liability limitations and indemnification
  - IP ownership assertions

- **Refund and Cancellation Policy** — `/refund`
  - Auto-renewing subscriptions via Lemon Squeezy
  - Cancel anytime (access until end of period)
  - Strict no-refund policy for digital access (with limited exceptions)
  - Chargeback warnings

- **End User License Agreement (EULA)** — `/license`
  - Specific to the desktop application and PyInstaller sidecar
  - License grant (non-exclusive, revocable, plan-dependent)
  - Strong restrictions (no reverse engineering, no redistribution)
  - "AS IS" warranty disclaimer + liability caps
  - References third-party components (Manim CE, Tauri, TinyTeX, etc.)

- **Acceptable Use Policy** — `/acceptable-use`
  - Rules for AI/chat abuse prevention
  - Prohibitions on harmful, illegal, or high-volume spam use
  - Enforcement rights (suspension, termination)

## Key Product Facts Relevant to Legal Protection

- **Proprietary software**: Matemium (the layout-to-animation compiler in `canvas/`, the desktop shell, cloud middleware) is proprietary. It is built on top of Manim Community Edition (MIT licensed) but the compiler, DSL, registry, builder API, desktop integration, and AI orchestration are original work.
- **Local execution only**: All rendering, Manim compilation, LaTeX (TinyTeX), and video encoding happens on the user's machine. The cloud never receives video files or full project directories.
- **Cloud is thin**: Auth (Supabase), billing (Lemon Squeezy webhooks), and LLM proxy only. AI receives only project excerpts (`scenes.py` + prompts) when the user explicitly uses chat/agent features.
- **Freemium licensing model**:
  - Free: Preview renders + limited AI
  - Pro: High/final quality, reel cutting, static exports, priority AI, multiple workspaces
  - Teams: Volume + admin features
- **User owns their content**: Lessons and videos created by users belong to users. AI processing grants only a limited license to Matemium for service delivery.

## Recommended Additional Steps Before Going Live

1. **Entity & Jurisdiction**
   - Decide on legal entity (e.g., LLC or corporation).
   - Choose governing law and venue in the Terms and EULA (currently placeholder language).
   - Update contact email and company name/address in all policies.

2. **Lemon Squeezy Store Settings**
   - Link the live policy URLs (Terms, Privacy, Refund) in your Lemon Squeezy store configuration.
   - Configure clear refund/cancellation language in the product description.

3. **Desktop App**
   - Display or link the EULA on first launch or in the installer.
   - Consider bundling a short LICENSE.txt or EULA acceptance dialog.
   - Ensure the sidecar and app binaries do not inadvertently include full source of proprietary components.

4. **LLM Provider Terms**
   - Review the terms of your LLM provider (OpenAI, Anthropic, etc.). They often prohibit certain uses and require you to pass through restrictions to end users (hence the Acceptable Use Policy).
   - Consider logging minimal metadata around AI usage for abuse detection without storing full prompts long-term.

5. **Marketing Claims**
   - Avoid absolute guarantees ("always accurate", "production-ready without review").
   - The current site language ("AI built in", "licensed desktop app") is appropriate but should be consistent with the disclaimers in the policies.

6. **Data Processing Addendum (DPA)**
   - For enterprise/Teams customers or EU users, prepare a simple DPA upon request.
   - Supabase and Lemon Squeezy already publish their own compliance documentation.

7. **Trademark**
   - Consider registering "Matemium" as a trademark in key jurisdictions if revenue justifies it.
   - Use proper attribution for Manim Community Edition where required.

8. **Regular Review**
   - Have policies reviewed by legal counsel once you have meaningful revenue or international users.
   - Date all policies and keep a change log (internal).

## File Locations (Website)

- `website/src/pages/PrivacyPolicyPage.tsx`
- `website/src/pages/TermsOfServicePage.tsx`
- `website/src/pages/RefundPolicyPage.tsx`
- `website/src/pages/EULAPage.tsx`
- `website/src/pages/AcceptableUsePage.tsx`

Routes are registered in `App.tsx`.

Footer links are maintained in `site-footer.tsx`.

Login consent text updated in `LoginPage.tsx`.

## Internal Documents

- `LEMON_SQUEEZY_SETUP.md` (billing integration)
- This `LEGAL.md`

---

**Disclaimer**: These documents are provided as a starting point tailored to the current architecture of Matemium. They are not a substitute for professional legal advice. Laws vary by jurisdiction. Consult qualified counsel before relying on these policies for commercial operations, especially once payments are live and users are in multiple countries.

Last reviewed: 2026-06-26
