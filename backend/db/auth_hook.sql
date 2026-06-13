-- auth_hook.sql — Supabase custom access token hook.
--
-- Adds `org_id` and `app_role` claims to every access token, read from
-- public.users. The backend (app/core/security.py) requires these claims.
--
-- Apply once in the Supabase SQL editor, then enable the hook:
--   Dashboard → Authentication → Hooks → Customize Access Token (JWT) →
--   select `public.custom_access_token_hook`.

create or replace function public.custom_access_token_hook(event jsonb)
returns jsonb
language plpgsql
stable
as $$
declare
  claims jsonb;
  u record;
begin
  select org_id, role into u
  from public.users
  where id = (event->>'user_id')::uuid;

  claims := coalesce(event->'claims', '{}'::jsonb);
  if u.org_id is not null then
    claims := jsonb_set(claims, '{org_id}', to_jsonb(u.org_id::text));
    claims := jsonb_set(claims, '{app_role}', to_jsonb(u.role));
  end if;

  return jsonb_set(event, '{claims}', claims);
end;
$$;

-- The hook runs as supabase_auth_admin; let it execute and read users.
grant execute on function public.custom_access_token_hook to supabase_auth_admin;
grant usage on schema public to supabase_auth_admin;
grant select on public.users to supabase_auth_admin;

-- RLS: allow the auth admin role to read users for the lookup above
-- (permissive, role-scoped — does not widen access for anyone else).
drop policy if exists users_auth_admin_read on public.users;
create policy users_auth_admin_read on public.users
  for select
  to supabase_auth_admin
  using (true);
