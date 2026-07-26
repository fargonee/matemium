const CHECKOUT_URL =
  "https://matemium.lemonsqueezy.com/checkout/buy/61dafc7d-d8a2-4968-beaf-8debf3fa6726?embed=1";

const FUNDS = [
  ["Agent inference", "Longer, more capable planning and project-management runs for shared development and evaluation."],
  ["Visual repair", "Automated render inspection, failure analysis, and repeated correction against real video evidence."],
  ["Evaluation", "A growing suite of mathematical projects that keeps agent behavior reliable as the system evolves."],
  ["Voice workflows", "Experiments in narration, provisional timing, transcription, and audio-led production."],
  ["Releases", "Build infrastructure, signing, distribution, storage, and cross-platform verification."],
  ["Time to maintain", "Space to fix bugs, answer users, improve documentation, and keep the source project healthy."],
];

export function SupportPage() {
  return (
    <>
      <section className="page-hero support-page-hero">
        <p className="section-kicker">Built freely. Sustained together.</p>
        <h1>Help Matemium reach<br /><span className="text-gradient italic">its next stage.</span></h1>
        <p>
          Matemium is a non-commercial, source-available project. The desktop app and
          rendering engine are largely built; contributions now make deeper agentic
          production and automation possible.
        </p>
        <a href={CHECKOUT_URL} className="lemonsqueezy-button button-primary mt-9">
          Contribute to Matemium <span aria-hidden>→</span>
        </a>
        <p className="mt-4 text-xs text-text-subtle">Voluntary, one-time support. No paid tier is unlocked.</p>
        <p className="mt-2 text-xs text-text-subtle">
          Checkout is processed by Lemon Squeezy. <a href="/refund" className="underline hover:text-text">Refund policy</a>
        </p>
      </section>

      <section className="section-shell pt-0">
        <div className="founder-note">
          <p className="section-kicker">A note from the maintainer</p>
          <blockquote>
            “I can continue building Matemium, but I cannot sustainably fund all of the
            AI inference, evaluation, and automation needed to deliver its most agentic
            experience alone.”
          </blockquote>
          <p>
            Matemium does not sell access, subscriptions, model credits, or your work.
            Support gives the project room to test ambitious workflows while keeping the
            core application available to educators, creators, students, and contributors.
          </p>
        </div>

        <div className="mt-24">
          <div className="section-heading">
            <div><p className="section-kicker">Where support goes</p><h2>Concrete work.<br /><span className="text-text-muted">Visible progress.</span></h2></div>
            <p className="max-w-md">
              Contributions are directed toward the parts of an AI-assisted creative tool
              that require recurring resources—not toward creating artificial feature gates.
            </p>
          </div>
          <div className="mt-12 grid gap-px overflow-hidden rounded-3xl border border-border bg-border sm:grid-cols-2 lg:grid-cols-3">
            {FUNDS.map(([title, body], index) => (
              <article key={title} className="bg-bg-card p-7">
                <span className="font-mono text-xs text-accent">0{index + 1}</span>
                <h3 className="mt-8 text-lg font-semibold">{title}</h3>
                <p className="mt-3 text-sm leading-6 text-text-muted">{body}</p>
              </article>
            ))}
          </div>
        </div>

        <div className="mt-24 grid gap-8 rounded-3xl border border-border bg-bg-elevated p-8 md:grid-cols-[1fr_auto] md:items-center md:p-12">
          <div>
            <p className="section-kicker">More than money</p>
            <h2 className="font-display text-4xl">Other ways to move Matemium forward.</h2>
            <p className="mt-4 max-w-2xl leading-7 text-text-muted">
              Create an example project, report a visual failure, test a release, improve
              documentation, translate the interface, submit code, or simply show someone
              what Matemium can make.
            </p>
          </div>
          <a
            href="https://github.com/fargonee/math/blob/main/CONTRIBUTING.md"
            target="_blank"
            rel="noreferrer"
            className="button-secondary"
          >
            Contribution guide <span aria-hidden>↗</span>
          </a>
        </div>

        <div className="mt-12 text-center">
          <a href={CHECKOUT_URL} className="lemonsqueezy-button button-primary">
            Support the next stage <span aria-hidden>→</span>
          </a>
        </div>
      </section>
    </>
  );
}
