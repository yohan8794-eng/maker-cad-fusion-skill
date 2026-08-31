create schema if not exists extensions;
create extension if not exists pgcrypto with schema extensions;

create table if not exists public.devices (
  id uuid primary key,
  pairing_code text not null unique check (pairing_code ~ '^[A-Z2-9]{10}$'),
  token_hash bytea not null,
  status text not null default 'offline' check (status in ('online', 'offline')),
  last_seen timestamptz,
  bridge_version text not null,
  created_at timestamptz not null default now()
);

create table if not exists public.cad_jobs (
  id uuid primary key default gen_random_uuid(),
  target_device_id uuid not null references public.devices(id) on delete cascade,
  status text not null default 'queued' check (status in ('queued', 'running', 'completed', 'failed')),
  input_json jsonb not null,
  result_json jsonb,
  error_message text,
  job_token_hash bytea not null,
  claimed_by uuid references public.devices(id),
  claimed_at timestamptz,
  completed_at timestamptz,
  created_at timestamptz not null default now()
);

create index if not exists cad_jobs_device_queue_idx
  on public.cad_jobs (target_device_id, status, created_at);
create index if not exists cad_jobs_claimed_by_idx on public.cad_jobs (claimed_by);

alter table public.devices enable row level security;
alter table public.cad_jobs enable row level security;
revoke all on public.devices, public.cad_jobs from anon, authenticated;
drop policy if exists "deny direct device access" on public.devices;
create policy "deny direct device access" on public.devices for all to anon, authenticated using (false) with check (false);
drop policy if exists "deny direct job access" on public.cad_jobs;
create policy "deny direct job access" on public.cad_jobs for all to anon, authenticated using (false) with check (false);

create or replace function public.register_device(
  p_device_id uuid, p_pairing_code text, p_device_token text, p_bridge_version text
) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare v_row public.devices;
begin
  if length(p_device_token) < 32 or p_pairing_code !~ '^[A-Z2-9]{10}$' then
    raise exception 'invalid device credentials';
  end if;
  insert into public.devices(id, pairing_code, token_hash, status, last_seen, bridge_version)
  values (p_device_id, p_pairing_code, extensions.digest(p_device_token, 'sha256'), 'online', now(), p_bridge_version)
  on conflict (id) do nothing;
  select * into v_row from public.devices where id = p_device_id;
  if v_row.token_hash is distinct from extensions.digest(p_device_token, 'sha256') then
    raise exception 'device authentication failed';
  end if;
  update public.devices set status='online', last_seen=now(), bridge_version=p_bridge_version where id=p_device_id;
  return jsonb_build_object('device_id', p_device_id, 'pairing_code', v_row.pairing_code, 'status', 'online');
end $$;

create or replace function public.device_heartbeat(
  p_device_id uuid, p_device_token text, p_bridge_version text
) returns jsonb
language plpgsql security definer set search_path = '' as $$
begin
  update public.devices set status='online', last_seen=now(), bridge_version=p_bridge_version
   where id=p_device_id and token_hash=extensions.digest(p_device_token, 'sha256');
  if not found then raise exception 'device authentication failed'; end if;
  return jsonb_build_object('status','online','last_seen',now());
end $$;

create or replace function public.resolve_pairing_code(p_pairing_code text)
returns jsonb language sql security definer set search_path = '' stable as $$
  select jsonb_build_object(
    'device_id', id,
    'status', case when last_seen >= now() - interval '90 seconds' then 'online' else 'offline' end,
    'last_seen', last_seen,
    'bridge_version', bridge_version
  ) from public.devices where pairing_code=upper(p_pairing_code)
$$;

create or replace function public.enqueue_cad_job(
  p_pairing_code text, p_input_json jsonb, p_job_token text
) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare v_device public.devices; v_job_id uuid;
begin
  if length(p_job_token) < 32 then raise exception 'invalid job token'; end if;
  select * into v_device from public.devices where pairing_code=upper(p_pairing_code);
  if not found then raise exception 'pairing code not found'; end if;
  if v_device.last_seen is null or v_device.last_seen < now() - interval '90 seconds' then
    raise exception 'bridge offline';
  end if;
  insert into public.cad_jobs(target_device_id,input_json,job_token_hash)
  values(v_device.id,p_input_json,extensions.digest(p_job_token,'sha256')) returning id into v_job_id;
  return jsonb_build_object('id',v_job_id,'status','queued','target_device_id',v_device.id);
end $$;

create or replace function public.get_cad_job_status(p_job_id uuid, p_job_token text)
returns jsonb language sql security definer set search_path = '' stable as $$
  select jsonb_build_object('id',id,'status',status,'result_json',result_json,
    'error_message',error_message,'created_at',created_at,'claimed_at',claimed_at,'completed_at',completed_at)
  from public.cad_jobs where id=p_job_id and job_token_hash=extensions.digest(p_job_token,'sha256')
$$;

create or replace function public.claim_next_cad_job(p_device_id uuid, p_device_token text)
returns jsonb language plpgsql security definer set search_path = '' as $$
declare v_job public.cad_jobs;
begin
  if not exists(select 1 from public.devices where id=p_device_id and token_hash=extensions.digest(p_device_token,'sha256')) then
    raise exception 'device authentication failed';
  end if;
  select * into v_job from public.cad_jobs
   where target_device_id=p_device_id and status='queued'
   order by created_at for update skip locked limit 1;
  if not found then return null; end if;
  update public.cad_jobs set status='running',claimed_by=p_device_id,claimed_at=now()
   where id=v_job.id and status='queued'
   returning * into v_job;
  if not found then return null; end if;
  return jsonb_build_object('id',v_job.id,'status',v_job.status,'input_json',v_job.input_json);
end $$;

create or replace function public.finish_cad_job(
  p_device_id uuid, p_device_token text, p_job_id uuid,
  p_status text, p_result_json jsonb default null, p_error_message text default null
) returns jsonb language plpgsql security definer set search_path = '' as $$
declare v_job public.cad_jobs;
begin
  if p_status not in ('completed','failed') then raise exception 'invalid terminal status'; end if;
  if not exists(select 1 from public.devices where id=p_device_id and token_hash=extensions.digest(p_device_token,'sha256')) then
    raise exception 'device authentication failed';
  end if;
  update public.cad_jobs set status=p_status,result_json=p_result_json,error_message=left(p_error_message,4000),completed_at=now()
   where id=p_job_id and target_device_id=p_device_id and claimed_by=p_device_id and status='running'
   returning * into v_job;
  if not found then raise exception 'job is not running on this device'; end if;
  return jsonb_build_object('id',v_job.id,'status',v_job.status,'completed_at',v_job.completed_at);
end $$;

revoke execute on function public.register_device(uuid,text,text,text) from public;
revoke execute on function public.device_heartbeat(uuid,text,text) from public;
revoke execute on function public.resolve_pairing_code(text) from public;
revoke execute on function public.enqueue_cad_job(text,jsonb,text) from public;
revoke execute on function public.get_cad_job_status(uuid,text) from public;
revoke execute on function public.claim_next_cad_job(uuid,text) from public;
revoke execute on function public.finish_cad_job(uuid,text,uuid,text,jsonb,text) from public;
grant execute on function public.register_device(uuid,text,text,text) to anon, authenticated;
grant execute on function public.device_heartbeat(uuid,text,text) to anon, authenticated;
grant execute on function public.resolve_pairing_code(text) to anon, authenticated;
grant execute on function public.enqueue_cad_job(text,jsonb,text) to anon, authenticated;
grant execute on function public.get_cad_job_status(uuid,text) to anon, authenticated;
grant execute on function public.claim_next_cad_job(uuid,text) to anon, authenticated;
grant execute on function public.finish_cad_job(uuid,text,uuid,text,jsonb,text) to anon, authenticated;
