# Supabase Setup

1. Create a Supabase project at https://supabase.com
2. Go to SQL Editor and run the contents of `schema.sql` (very important — this creates the `profiles` table etc.).
3. Skip billing migrations for the current free product unless schema compatibility with historical deployments is required.
4. Billing (Lemon Squeezy) columns are historical. See root `LEMON_SQUEEZY_SETUP.md` only if paid offerings are deliberately reintroduced.
5. Copy the **Project URL** and **anon public** key into your hosting env:
   - `VITE_SUPABASE_URL`
   - `VITE_SUPABASE_ANON_KEY`
6. For the server, also copy the **service_role** key as `MATEMIUM_SUPABASE_SERVICE_ROLE_KEY` (keep secret).
7. In Supabase Dashboard → Authentication → URL Configuration:
   - Site URL: your final site (e.g. `https://your-project.pages.dev`)
   - Redirect URLs: add the same + `https://your-project.pages.dev/**/auth/callback`, preview URLs (`https://*.pages.dev/**/auth/callback`), and any custom domains
8. Optionally create a `profiles` row policy / trigger already covers signups via the included `handle_new_user`.

## Row Level Security
- Users can read/update their own profile.
- Historical subscription rows are readable by owner if present.
- Server uses service role key to read/write on behalf of users and for profile/admin operations.

## After first deploy
- Sign in with Google on the live site.
- Promote yourself to admin (SQL):
  ```sql
  update public.profiles set role = 'admin' where email = 'you@example.com';
  ```
