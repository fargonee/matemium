/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_SUPABASE_URL: string;
  readonly VITE_SUPABASE_ANON_KEY: string;
  readonly VITE_SITE_URL: string;
  readonly VITE_API_URL: string;
  readonly VITE_ADMIN_EMAILS?: string;
  /** Base public path for GitHub Pages sub-directory hosting (e.g. "/repo/"). Set via VITE_BASE build env. */
  readonly BASE_URL: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}