import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

const FEATURES = [
  {
    title: "Infinite learning sheet",
    body: "Content anchors on the XY plane. The camera pans down; elements reveal lazily and persist in a registry.",
  },
  {
    title: "Reels & YouTube",
    body: "Portrait 9:16 by default. Landscape 16:9 for YouTube. Long lessons auto-chunk into vertical clips.",
  },
  {
    title: "CSS-like layout",
    body: "Flex rows, inline styled runs, margins, and widths — declarative structure instead of hand-positioning frames.",
  },
  {
    title: "3D when you need it",
    body: "Surfaces, solids, camera inspect paths, and isolate-zoom focus without thrashing between 2D and 3D.",
  },
  {
    title: "Desktop app",
    body: "Code editor, AI assistant, live preview, and bundled local rendering — no cloud video pipeline.",
  },
  {
    title: "Static export",
    body: "Export the full reasoning tape as PNG or PDF study material in natural aspect ratio.",
  },
];

export function HomePage() {
  return (
    <>
      <section className="relative overflow-hidden px-4 pb-20 pt-16">
        <div
          className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_80%_60%_at_70%_20%,rgba(45,91,255,0.18),transparent),radial-gradient(ellipse_50%_40%_at_20%_80%,rgba(110,231,168,0.06),transparent)]"
          aria-hidden
        />
        <div className="relative mx-auto grid max-w-6xl gap-12 lg:grid-cols-2 lg:items-center">
          <div>
            <p className="mb-3 text-sm font-semibold uppercase tracking-wider text-accent">
              Free desktop app
            </p>
            <h1 className="text-4xl font-bold tracking-tight md:text-5xl">
              Math lessons that scroll like a document, animate like a film
            </h1>
            <p className="mt-5 max-w-xl text-lg text-text-muted">
              Matemium is a layout-to-animation compiler for educators and creators.
              Describe your lesson on an infinite vertical learning sheet — the app
              handles layout, camera movement, local rendering, and social-ready exports.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link to="/login">
                <Button size="lg">Sign in to get started</Button>
              </Link>
              <Link to="/pricing">
                <Button variant="secondary" size="lg">
                  Free access
                </Button>
              </Link>
            </div>
            <ul className="mt-8 flex flex-wrap gap-6 text-sm text-text-subtle">
              <li>
                <strong className="block text-base text-text">9:16</strong> reels-first
              </li>
              <li>
                <strong className="block text-base text-text">Local</strong> rendering
              </li>
              <li>
                <strong className="block text-base text-text">Flexible AI</strong> built in
                <span className="text-xs text-text-muted"> — your provider keys or local models</span>
              </li>
            </ul>
          </div>

          <div className="mx-auto w-full max-w-sm" aria-hidden>
            <div className="rounded-[20px] border-2 border-border-strong bg-bg-elevated p-4 shadow-2xl">
              <div className="mb-3 text-center text-[10px] font-semibold uppercase tracking-wider text-text-subtle">
                9:16 viewport
              </div>
              <div className="space-y-2">
                <div className="rounded-lg border border-accent/30 bg-accent/10 px-3 py-2 text-sm font-semibold">
                  Quadratic factoring
                </div>
                <div className="rounded-lg border border-border bg-bg-card px-3 py-2 text-center font-mono text-sm">
                  x² − 5x + 6 = 0
                </div>
                <div className="rounded-lg border border-border bg-bg-card px-3 py-2 text-xs text-text-muted">
                  Find two numbers: ×6, sum −5
                </div>
                <div className="rounded-lg border border-accent px-3 py-2 text-center font-mono text-sm">
                  (x − 2)(x − 3) = 0
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section id="features" className="border-y border-border bg-bg-elevated px-4 py-20">
        <div className="mx-auto max-w-6xl">
          <div className="mb-10 max-w-2xl">
            <p className="mb-2 text-sm font-semibold uppercase tracking-wider text-accent">
              Why Matemium
            </p>
            <h2 className="text-3xl font-bold tracking-tight">A document compiler for animated math</h2>
            <p className="mt-3 text-text-muted">
              Traditional animation tools are sequence-oriented. Matemium models a continuous
              reasoning tape — earlier steps stay visible and the camera scrolls down.
            </p>
          </div>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map((feature) => (
              <Card key={feature.title}>
                <h3 className="font-semibold">{feature.title}</h3>
                <p className="mt-2 text-sm text-text-muted">{feature.body}</p>
              </Card>
            ))}
          </div>
        </div>
      </section>

      <section className="px-4 py-20">
        <div className="mx-auto max-w-3xl text-center">
          <h2 className="text-3xl font-bold tracking-tight">Ready to create?</h2>
          <p className="mt-3 text-text-muted">
            Sign in with Google, download the desktop app, and connect OpenRouter
            locally from your computer.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <Link to="/login">
              <Button size="lg">Sign in</Button>
            </Link>
            <Link to="/pricing">
              <Button variant="secondary" size="lg">
                Free access
              </Button>
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
