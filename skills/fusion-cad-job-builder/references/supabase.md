# Supabase job bridge

Use `SUPABASE_URL` and `SUPABASE_PUBLISHABLE_KEY` (legacy `SUPABASE_KEY` is accepted for compatibility). Never bundle a service-role key in a client/Add-in.

Suggested table:

```sql
create table public.cad_jobs (
  id uuid primary key default gen_random_uuid(),
  status text not null default 'queued' check (status in ('queued','claimed','running','succeeded','failed')),
  job jsonb not null,
  result jsonb,
  error text,
  runner_id text,
  claimed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
alter table public.cad_jobs enable row level security;
```

Grant only the required Data API privileges and add policies matching the actual authenticated runner identity. A publishable key identifies the application; RLS must still authorize rows. Do not create permissive `anon` update policies for a production runner.

The packaged REST client is deliberately dependency-free and supports enqueue/read/update. Atomic multi-runner claiming should be implemented as a database function after the authentication model is decided; the MVP Add-in is safe only for a single runner.
