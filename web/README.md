# Web — Next.js dashboard

Login + an **Ask** page that queries the backend `POST /brain/query` and shows the
grounded answer with sources.

## Stack
- Next.js (App Router) + TypeScript
- Supabase Auth (browser client)

## Run locally
```bash
cd web
cp .env.local.example .env.local   # fill in the 3 values
npm install
npm run dev                        # http://localhost:3000
```

`.env.local`:
- `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` — Supabase → Settings → API
- `NEXT_PUBLIC_API_BASE_URL` — the FastAPI backend (default `http://localhost:8000`)

The backend must be running and allow this origin (CORS_ORIGINS defaults to
`http://localhost:3000`).

## One-time Supabase setup (required for auth to reach the backend)

The backend needs `org_id` + `app_role` in the JWT. Wire it up once:

1. **Install the access-token hook**: run `backend/db/auth_hook.sql` in the
   Supabase SQL editor, then enable it under
   *Authentication → Hooks → Customize Access Token (JWT)* →
   `public.custom_access_token_hook`.
2. **Create a test user** and link it to an org:
   - *Authentication → Users → Add user* (email + password). Copy its UUID.
   - In SQL editor, insert the matching app user (Org A from the seed):
     ```sql
     -- run with FORCE RLS lifted, or as a bypass role:
     alter table users no force row level security;
     insert into users (id, org_id, email, full_name, role)
     values ('<auth-user-uuid>',
             '00000000-0000-0000-0000-000000000001',
             '<email>', 'Test User', 'admin')
     on conflict (id) do update set org_id = excluded.org_id, role = excluded.role;
     alter table users force row level security;
     ```
3. Sign in on the web app with that email/password, then ask
   *"What did we promise Acme about delivery and pricing?"* — you should get the
   grounded answer with sources (if you ran the RAG demo to ingest Acme data).
