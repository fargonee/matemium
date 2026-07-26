import { Link } from "react-router-dom";

import { OutputCard } from "@/components/output-card";

const PROJECTS = [
  {
    title: "Quadratic graphs",
    description: "Compare parabolas side by side and watch each coefficient change the graph in a predictable way.",
    video: "/media/quadratic-graphs.mp4",
    poster: "/media/quadratic-graphs.jpg",
    accent: "violet" as const,
  },
  {
    title: "Quadratic factoring",
    description: "A continuous derivation that keeps earlier reasoning visible as the camera moves through the solution.",
    video: "/media/quadratic-factoring.mp4",
    poster: "/media/quadratic-factoring.jpg",
    accent: "cyan" as const,
  },
  {
    title: "Electromagnetic waves",
    description: "A multi-section physics lesson combining notation, explanation, spatial motion, and mathematical surfaces.",
    video: "/media/em-waves.mp4",
    poster: "/media/em-waves.jpg",
    accent: "cyan" as const,
  },
  {
    title: "Inscribed sphere",
    description: "A cube, an inscribed sphere, dimensional labels, and a moving camera within the same reasoning tape.",
    video: "/media/inscribed-sphere.mp4",
    poster: "/media/inscribed-sphere.jpg",
    accent: "amber" as const,
  },
];

export function ShowcasePage() {
  return (
    <>
      <section className="page-hero">
        <p className="section-kicker">Made with Matemium</p>
        <h1>Mathematics,<br /><span className="text-gradient italic">in motion.</span></h1>
        <p>
          Real output from the Matemium rendering engine—not concept art. Play each
          excerpt to see document-like reasoning become a film.
        </p>
      </section>
      <section className="section-shell pt-0">
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {PROJECTS.map((project, index) => (
            <OutputCard key={project.title} {...project} eager={index === 0} />
          ))}
        </div>
        <div className="mt-20 grid gap-6 rounded-3xl border border-border bg-bg-elevated p-8 md:grid-cols-3 md:p-12">
          <div>
            <span className="section-kicker">One engine</span>
            <h2 className="mt-3 font-display text-4xl">Many destinations.</h2>
          </div>
          <p className="text-sm leading-7 text-text-muted">
            Start with a portrait reasoning tape for Shorts and Reels, or render the
            same kind of structured lesson for a landscape presentation.
          </p>
          <p className="text-sm leading-7 text-text-muted">
            Export the complete sheet as PNG or PDF when the explanation should remain
            visible as study material instead of disappearing with the timeline.
          </p>
        </div>
        <div className="mt-12 text-center">
          <Link to="/download" className="button-primary">Create with Matemium <span aria-hidden>→</span></Link>
        </div>
      </section>
    </>
  );
}
