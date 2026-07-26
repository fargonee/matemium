import { Link } from "react-router-dom";

type Accent = "violet" | "cyan" | "amber";

interface OutputCardProps {
  slug: string;
  title: string;
  subjectLabel: string;
  question: string;
  description: string;
  video: string;
  poster: string;
  accent: Accent;
  duration: string;
  capabilities?: string[];
  eager?: boolean;
}

export function OutputCard({
  slug,
  title,
  subjectLabel,
  question,
  description,
  video,
  poster,
  accent,
  duration,
  capabilities = [],
  eager = false,
}: OutputCardProps) {
  return (
    <article className={`output-card output-card-${accent}`}>
      <div className="output-media">
        <video
          muted
          loop
          playsInline
          controls
          poster={poster}
          preload={eager ? "metadata" : "none"}
          aria-label={`${title} animation made with Matemium`}
          onMouseEnter={(event) => {
            void event.currentTarget.play().catch(() => undefined);
          }}
          onMouseLeave={(event) => {
            event.currentTarget.pause();
          }}
        >
          <source src={video} type="video/mp4" />
        </video>
        <span className="output-format">9:16 · {duration}</span>
      </div>
      <div className="p-6">
        <span className="font-mono text-[9px] uppercase tracking-[0.16em] text-text-subtle">{subjectLabel}</span>
        <h3 className="mt-3 text-lg font-semibold">{title}</h3>
        <p className="mt-2 text-sm font-medium leading-6 text-text">{question}</p>
        <p className="mt-2 text-sm leading-6 text-text-muted">{description}</p>
        {capabilities.length > 0 ? (
          <div className="mt-5 flex flex-wrap gap-1.5">
            {capabilities.slice(0, 2).map((capability) => (
              <span key={capability} className="capability-chip">{capability}</span>
            ))}
          </div>
        ) : null}
        <Link to={`/showcase/${slug}`} className="text-link mt-6">
          View case study <span aria-hidden>→</span>
        </Link>
      </div>
    </article>
  );
}
