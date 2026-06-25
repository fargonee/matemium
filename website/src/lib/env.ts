export const env = {
  supabaseUrl: import.meta.env.VITE_SUPABASE_URL ?? "",
  supabaseAnonKey: import.meta.env.VITE_SUPABASE_ANON_KEY ?? "",
  siteUrl: import.meta.env.VITE_SITE_URL ?? (typeof window !== "undefined" ? window.location.origin : ""),
  apiUrl: import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8080",
  adminEmails: import.meta.env.VITE_ADMIN_EMAILS ?? "",
};