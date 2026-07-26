type Accent = "violet" | "cyan" | "amber";

interface OutputCardProps {
  title: string;
  description: string;
  video: string;
  poster: string;
  accent: Accent;
  eager?: boolean;
}

export function OutputCard({
  title,
  description,
  video,
  poster,
  accent,
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
        <span className="output-format">9:16 · Local render</span>
      </div>
      <div className="p-6">
        <h3 className="text-lg font-semibold">{title}</h3>
        <p className="mt-2 text-sm leading-6 text-text-muted">{description}</p>
      </div>
    </article>
  );
}
