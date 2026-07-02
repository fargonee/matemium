interface ObsidianLoadingScreenProps {
  progress?: number; // 0-100
  message?: string;
  phase?: string;
  onBrowseGallery?: () => void;
  onRetry?: () => void;
}

export function ObsidianLoadingScreen({
  progress = 0,
  message = "Preparing the local rendering engine and assets…",
  phase,
  onBrowseGallery,
  onRetry,
}: ObsidianLoadingScreenProps) {
  const displayProgress = Math.max(0, Math.min(100, progress || 0));

  return (
    <div className="obsidian-loading">
      <div className="loading-content">
        <div className="logo">
          <span className="matemium-text">Matemium</span>
        </div>

        <h2 className="loading-title">Initializing local engine</h2>

        <div className="loading-message">{message}</div>

        {phase && <div className="loading-phase">{phase}</div>}

        <div className="progress-container">
          <div className="progress-bar">
            <div
              className="progress-fill"
              style={{ width: `${displayProgress}%` }}
            />
          </div>
          <div className="progress-text">{Math.floor(displayProgress)}%</div>
        </div>

        <div className="loading-actions">
          {onBrowseGallery && (
            <button className="btn btn-secondary" onClick={onBrowseGallery}>
              Browse Gallery
            </button>
          )}
          {onRetry && (
            <button className="btn btn-ghost" onClick={onRetry}>
              Check again
            </button>
          )}
        </div>

        <p className="loading-footnote">
          All heavy computation happens locally. Public content works immediately.
        </p>
      </div>

      <div className="loading-bg-effects">
        <div className="neon-glow" />
      </div>
    </div>
  );
}
