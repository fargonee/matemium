# Supabase Setup

1. Create a Supabase project at https://supabase.com
2. Go to SQL Editor and run the contents of `schema.sql`.
3. (If you previously used Stripe columns) run `migrations/002_lemon_squeezy.sql`.
4. Copy the **Project URL** and **anon public** key into your hosting env:
   - `VITE_SUPABASE_URL`
   - `VITE_SUPABASE_ANON_KEY`
5. For the server, also copy the **service_role** key as `MATEMIUM_SUPABASE_SERVICE_ROLE_KEY` (keep secret).
6. In Supabase Dashboard → Authentication → URL Configuration:
   - Site URL: your final site (e.g. `https://your-project.pages.dev`)
   - Redirect URLs: add the same + `https://your-project.pages.dev/**/auth/callback`, preview URLs (`https://*.pages.dev/**/auth/callback`), and any custom domains
7. Optionally create a `profiles` row policy / trigger already covers signups via the included `handle_new_user`.

## Row Level Security
- Users can read/update their own profile.
- Subscriptions are readable by owner.
- Server uses service role key to read/write on behalf of users and for webhooks/admin.

## After first deploy
- Sign in with Google on the live site.
- Promote yourself to admin (SQL):
  ```sql
  update public.profiles set role = 'admin' where email = 'you@example.com';
  ```
