export const env = {
  supabaseUrl: import.meta.env.VITE_SUPABASE_URL ?? "",
  supabaseAnonKey: import.meta.env.VITE_SUPABASE_ANON_KEY ?? "",
  siteUrl: import.meta.env.VITE_SITE_URL ?? (typeof window !== "undefined" ? window.location.origin : ""),
  apiUrl: import.meta.env.VITE_API_URL ?? "https://p01--math--zjvwyx4fjqbn.code.run",
  adminEmails: import.meta.env.VITE_ADMIN_EMAILS ?? "",
};