const REPO = "fargonee/matemium";
const RELEASES_URL = `https://github.com/${REPO}/releases`;
const LATEST_RELEASE_API = `https://api.github.com/repos/${REPO}/releases/latest`;
const LOCAL_RELEASE_MANIFEST = `${import.meta.env.BASE_URL}downloads/latest.json`;

export type DownloadPlatform = "linux" | "windows" | "macos";

export interface ReleaseAsset {
  id: number;
  name: string;
  size: number;
  browser_download_url: string;
}

export interface LatestRelease {
  tagName: string;
  name: string;
  htmlUrl: string;
  publishedAt: string | null;
  assets: ReleaseAsset[];
}

export interface DownloadLink {
  label: string;
  href: string;
  sizeLabel: string;
}

interface GitHubReleaseResponse {
  tag_name: string;
  name: string | null;
  html_url: string;
  published_at: string | null;
  assets: ReleaseAsset[];
}

let latestReleasePromise: Promise<LatestRelease | null> | null = null;

export function getReleasesUrl(): string {
  return RELEASES_URL;
}

export function loadLatestRelease(): Promise<LatestRelease | null> {
  latestReleasePromise ??= loadLocalReleaseManifest().then((localRelease) => {
    if (localRelease?.assets.length) return localRelease;
    return loadGitHubLatestRelease();
  });

  return latestReleasePromise;
}

function loadLocalReleaseManifest(): Promise<LatestRelease | null> {
  return fetch(LOCAL_RELEASE_MANIFEST, { cache: "no-cache" })
    .then((response) => {
      if (!response.ok) return null;
      return response.json() as Promise<LatestRelease>;
    })
    .then((release) => {
      if (!release?.tagName || !Array.isArray(release.assets)) return null;
      return release;
    })
    .catch(() => null);
}

function loadGitHubLatestRelease(): Promise<LatestRelease | null> {
  return fetch(LATEST_RELEASE_API, {
    headers: { Accept: "application/vnd.github+json" },
  })
    .then((response) => {
      if (!response.ok) return null;
      return response.json() as Promise<GitHubReleaseResponse>;
    })
    .then((release) => {
      if (!release) return null;
      return {
        tagName: release.tag_name,
        name: release.name || release.tag_name,
        htmlUrl: release.html_url,
        publishedAt: release.published_at,
        assets: release.assets || [],
      };
    })
    .catch(() => null);
}

export function getPlatformLinks(
  release: LatestRelease | null,
  platform: DownloadPlatform,
): DownloadLink[] {
  if (!release) return [];

  return release.assets
    .filter((asset) => assetMatchesPlatform(asset.name, platform))
    .sort((a, b) => assetSortWeight(a.name) - assetSortWeight(b.name))
    .map((asset) => ({
      label: assetLabel(asset.name),
      href: asset.browser_download_url,
      sizeLabel: formatBytes(asset.size),
    }));
}

export function formatReleaseDate(value: string | null): string {
  if (!value) return "";
  return new Intl.DateTimeFormat(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(new Date(value));
}

function assetMatchesPlatform(name: string, platform: DownloadPlatform): boolean {
  const lower = name.toLowerCase();
  if (platform === "linux") {
    return lower.endsWith(".deb") || lower.endsWith(".appimage");
  }
  if (platform === "windows") {
    return lower.endsWith(".exe") || lower.endsWith(".msi");
  }
  return lower.endsWith(".dmg");
}

function assetSortWeight(name: string): number {
  const lower = name.toLowerCase();
  if (lower.endsWith(".deb")) return 10;
  if (lower.endsWith(".appimage")) return 20;
  if (lower.endsWith(".exe")) return 10;
  if (lower.endsWith(".msi")) return 20;
  if (lower.includes("arm64") || lower.includes("aarch64")) return 10;
  if (lower.includes("x64") || lower.includes("x86_64") || lower.includes("intel")) return 20;
  if (lower.endsWith(".dmg")) return 30;
  return 100;
}

function assetLabel(name: string): string {
  const lower = name.toLowerCase();
  if (lower.endsWith(".deb")) return "Download .deb";
  if (lower.endsWith(".appimage")) return "Download AppImage";
  if (lower.endsWith(".exe")) return "Download .exe";
  if (lower.endsWith(".msi")) return "Download .msi";
  if (lower.endsWith(".dmg")) {
    if (lower.includes("arm64") || lower.includes("aarch64")) return "Download macOS Apple Silicon";
    if (lower.includes("x64") || lower.includes("x86_64") || lower.includes("intel")) return "Download macOS Intel";
    return "Download .dmg";
  }
  return name;
}

function formatBytes(size: number): string {
  if (!Number.isFinite(size) || size <= 0) return "";
  const units = ["B", "KB", "MB", "GB"];
  let value = size;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${value >= 10 || unit === 0 ? value.toFixed(0) : value.toFixed(1)} ${units[unit]}`;
}
