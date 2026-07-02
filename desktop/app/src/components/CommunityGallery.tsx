import React from "react";
import * as api from "../api/tauri";

interface GalleryItem {
  id: string;
  title: string;
  description?: string;
  youtube_id?: string;
  tags?: string[];
  author_name?: string;
  status?: string;
}

interface CommunityGalleryProps {
  onClose?: () => void;
}

export function CommunityGallery({ onClose }: CommunityGalleryProps) {
  const [search, setSearch] = React.useState("");
  const [items, setItems] = React.useState<GalleryItem[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [selected, setSelected] = React.useState<GalleryItem | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  const loadGallery = React.useCallback(async (q?: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.listGallery(q);
      const list = (res.items || res || []) as GalleryItem[];
      setItems(list);
    } catch (e: any) {
      setError(String(e));
      // Fallback to skeleton on error
      setItems([
        { id: "demo-quadratic", title: "Quadratic Factoring", description: "Visual proof...", youtube_id: "M7lc1UVf-VE", tags: ["algebra"], author_name: "Matemium Demo" },
        { id: "demo-waves", title: "Electromagnetic Waves", description: "3D EM waves...", youtube_id: "jNQXAC9IVRw", tags: ["physics"], author_name: "Community" },
      ]);
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    void loadGallery();
  }, [loadGallery]);

  React.useEffect(() => {
    const t = setTimeout(() => { void loadGallery(search); }, 300);
    return () => clearTimeout(t);
  }, [search, loadGallery]);

  const filtered = items.filter((item) => {
    const q = search.toLowerCase();
    return (
      item.title.toLowerCase().includes(q) ||
      (item.description || "").toLowerCase().includes(q) ||
      ((item.tags || []) as string[]).some((t) => t.toLowerCase().includes(q))
    );
  });

  return (
    <div className="gallery-container">
      <div className="gallery-header">
        <h2>Community Gallery</h2>
        <p className="gallery-subtitle">Public animations powered by YouTube. Works before local engines are ready.</p>
        <div className="gallery-controls">
          <input
            type="text"
            placeholder="Search titles, tags..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="gallery-search"
          />
          {onClose && (
            <button className="btn btn-ghost" onClick={onClose}>
              Close
            </button>
          )}
        </div>
      </div>

      {loading && <div>Loading gallery...</div>}
      {error && <div style={{color: '#f55'}}>Error loading: {error} (using fallback)</div>}

      <div className="gallery-grid">
        {filtered.map((item) => {
          const yt = (item as any).youtube_id || (item as any).youtubeId || '';
          const tags = (item.tags || []) as string[];
          const author = item.author_name || (item as any).author;
          return (
            <div
              key={item.id}
              className="gallery-card"
              onClick={() => setSelected(item)}
            >
              <div className="gallery-thumb">
                {yt && (
                  <img
                    src={`https://img.youtube.com/vi/${yt}/hqdefault.jpg`}
                    alt={item.title}
                    onError={(e) => {
                      (e.target as HTMLImageElement).src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='320' height='180'%3E%3Crect width='100%25' height='100%25' fill='%23111'/%3E%3Ctext x='50%25' y='50%25' fill='%23666' font-size='14' text-anchor='middle'%3EMatemium%3C/text%3E%3C/svg%3E";
                    }}
                  />
                )}
                <div className="play-overlay">▶</div>
              </div>
              <div className="gallery-meta">
                <h3>{item.title}</h3>
                <p className="desc">{item.description}</p>
                <div className="tags">
                  {tags.map((tag: string) => (
                    <span key={tag} className="tag">{tag}</span>
                  ))}
                </div>
                {author && <span className="author">by {author}</span>}
                {item.status && <span style={{fontSize: '0.65rem', color: '#888'}}> • {item.status}</span>}
              </div>
            </div>
          );
        })}
        {filtered.length === 0 && !loading && <div className="empty">No results. Try different search.</div>}
      </div>

      {selected && (
        <div className="gallery-modal" onClick={() => setSelected(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close" onClick={() => setSelected(null)}>✕</button>
            <h3>{selected.title}</h3>
            <div className="video-wrapper">
              <iframe
                width="100%"
                height="400"
                src={`https://www.youtube.com/embed/${(selected as any).youtube_id || (selected as any).youtubeId}?autoplay=1`}
                title={selected.title}
                frameBorder="0"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowFullScreen
              />
            </div>
            <p>{selected.description}</p>
            <div className="meta-footer">
              <span>Public community animation • Plays via YouTube (no local render needed)</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
