# Matemium Legal Documentation

This document summarizes all legal and policy materials for the Matemium project (desktop application + website + cloud services).

## Core Policies (Published on Website)

These pages are implemented as React routes in the marketing/dashboard website:

- **Privacy Policy** — `/privacy`
  - Data collection (optional Supabase auth, user profile data, user-selected LLM provider context)
  - Local-only rendering (no media uploaded)
  - Third parties: Supabase, OpenRouter/user-selected LLM providers
  - User rights and data retention

- **Terms of Service** — `/terms`
  - Account rules
  - Free use terms and source-available license restrictions
  - User content ownership + limited license grant for AI processing
  - AI disclaimers (assistive only)
  - Broad liability limitations and indemnification
  - IP ownership assertions

- **Refund and Cancellation Policy** — `/refund`
  - Historical only unless paid offerings are reintroduced.
  - Current product policy: Matemium does not charge users, sell subscriptions, or sell AI credits.

- **Source-Available Software License** — `/license`
  - Specific to the desktop application, bundled sidecar, and Matemium source tree
  - License grant for inspection, personal use, education, internal use, and contribution to the official project
  - Private modifications permitted
  - Redistribution, publication of derivative builds, commercial use, and operation of competing forks require written permission
  - "AS IS" warranty disclaimer + liability caps
  - References third-party components (Manim CE, Tauri, TinyTeX, etc.)

- **Acceptable Use Policy** — `/acceptable-use`
  - Rules for AI/chat abuse prevention
  - Prohibitions on harmful, illegal, or high-volume spam use
  - Enforcement rights (suspension, termination)

## Key Product Facts Relevant to Legal Protection

- **Source-available software**: Matemium's source code is publicly available for inspection, personal use, education, and contribution to the official project under the Matemium Source-Available License. Private modifications are allowed. Redistribution, publication of derivative builds, commercial use, and competing forks require written permission.
- **Local execution only**: All rendering, Manim compilation, LaTeX (TinyTeX), and video encoding happens on the user's machine. The cloud never receives video files or full project directories.
- **Cloud is thin and optional**: Auth/profile sync and BYO LLM routing helpers only. AI receives only project excerpts (`scenes.py` + prompts) when the user explicitly uses chat/agent features.
- **No monetization**: Matemium does not sell subscriptions, charge for app access, resell AI model access, or provide in-app AI tokens.
- **AI provider ownership**: Users connect their own OpenRouter or other provider API keys. Provider billing, limits, and terms belong to the user's chosen provider.
- **User owns their content**: Lessons and videos created by users belong to users. AI processing grants only a limited license to Matemium for service delivery.

## Recommended Additional Steps Before Going Live

1. **Entity & Jurisdiction**
   - Decide on legal entity (e.g., LLC or corporation).
   - Choose governing law and venue in the Terms and EULA (currently placeholder language).
   - Update contact email and company name/address in all policies.

2. **Payment Infrastructure**
   - Treat Lemon Squeezy and subscription language as historical unless paid offerings are deliberately reintroduced.
   - Remove checkout and billing references from public policy pages before launch if the free model remains final.

3. **Desktop App**
   - Display or link the EULA on first launch or in the installer.
   - Consider bundling a short LICENSE.txt or license acceptance dialog.
   - Bundle clear license text explaining inspection, personal/internal use, contribution, private modification, and restricted redistribution/commercial forks.

4. **LLM Provider Terms**
   - Review OpenRouter and any directly supported provider terms. Users bring their own keys, but Matemium should still explain that provider usage is governed by the provider's policies.
   - Avoid storing provider keys in Matemium cloud unless explicitly necessary; prefer local secure storage for desktop use.

5. **Marketing Claims**
   - Avoid absolute guarantees ("always accurate", "production-ready without review").
   - The current site language ("AI built in", "licensed desktop app") is appropriate but should be consistent with the disclaimers in the policies.

6. **Data Processing Addendum (DPA)**
   - If cloud profile sync or hosted collaboration expands, prepare a simple DPA upon request.
   - Supabase and OpenRouter/provider compliance docs should be linked where relevant.

7. **Trademark**
   - Consider registering "Matemium" as a trademark in key jurisdictions if revenue justifies it.
   - Use proper attribution for Manim Community Edition where required.

8. **Regular Review**
   - Have policies reviewed by legal counsel before launch and before any future paid or commercial licensing changes.
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

- `LEMON_SQUEEZY_SETUP.md` (historical billing integration; not current product policy)
- This `LEGAL.md`

---

**Disclaimer**: These documents are provided as a starting point tailored to the current architecture of Matemium. They are not a substitute for professional legal advice. Laws vary by jurisdiction. Consult qualified counsel before relying on these policies for commercial operations, especially once payments are live and users are in multiple countries.

Last reviewed: 2026-07-26
