import { Link } from "react-router-dom";

import { SocialLinkGrid } from "@/components/social-links";
import { CONTACT_EMAIL } from "@/content/socials";

export function ConnectPage() {
  return (
    <>
      <section className="page-hero connect-page-hero">
        <p className="section-kicker">Find Matemium</p>
        <h1>Follow the build.<br /><span className="text-gradient italic">Join the conversation.</span></h1>
        <p>
          See new visual explanations, follow release work, read the technical
          story, or talk directly with the person building Matemium.
        </p>
        <div className="mt-9 flex flex-wrap justify-center gap-3">
          <a href="https://youtube.com/@matemium" target="_blank" rel="noreferrer" className="button-primary">
            Watch on YouTube <span aria-hidden>↗</span>
          </a>
          <a href={`mailto:${CONTACT_EMAIL}`} className="button-secondary">
            Email Matemium
          </a>
        </div>
      </section>

      <section className="section-shell pt-0">
        <div className="connect-intro">
          <div>
            <p className="section-kicker">One project, many places</p>
            <h2 className="font-display text-4xl md:text-5xl">Choose the channel that feels like yours.</h2>
          </div>
          <p>
            Videos live on YouTube and Instagram. Release work happens on GitHub.
            Telegram, Reddit, X, and Bluesky carry the ongoing conversation, while
            DEV goes deeper into how the system is made.
          </p>
        </div>
        <SocialLinkGrid />

        <div className="connect-contact-card">
          <div>
            <span className="social-link-mark" aria-hidden>@</span>
            <div>
              <p className="section-kicker">Direct contact</p>
              <h2>Have a question, collaboration, or story?</h2>
            </div>
          </div>
          <div>
            <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>
            <p>For support, press, partnerships, education, and everything that deserves a real conversation.</p>
          </div>
        </div>

        <div className="mt-12 flex flex-wrap items-center justify-between gap-5 border-t border-border pt-10">
          <p className="max-w-2xl text-sm leading-6 text-text-muted">
            Want to contribute code or documentation? GitHub remains the canonical
            home for issues, pull requests, releases, and project history.
          </p>
          <Link to="/source" className="button-secondary">Source and contribution paths</Link>
        </div>
      </section>
    </>
  );
}
