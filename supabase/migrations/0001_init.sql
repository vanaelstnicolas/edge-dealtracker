create extension if not exists "pgcrypto";

create table if not exists public.users (
  id uuid primary key default gen_random_uuid(),
  email text unique not null,
  full_name text not null,
  whatsapp_number text unique,
  created_at timestamptz not null default now()
);

do $$
begin
  if not exists (select 1 from pg_type where typname = 'deal_status') then
    create type deal_status as enum ('active', 'won', 'lost');
  end if;
end
$$;

create table if not exists public.deals (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references public.users(id),
  company text not null,
  description text not null,
  action text not null,
  deadline date not null,
  status deal_status not null default 'active',
  created_at timestamptz not null default now(),
  closed_at timestamptz
);

create index if not exists deals_owner_idx on public.deals(owner_id);
create index if not exists deals_status_idx on public.deals(status);
create index if not exists deals_deadline_idx on public.deals(deadline);
