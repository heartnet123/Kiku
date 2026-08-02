-- Create public.users table if it does not exist
create table if not exists public.users (
    id uuid primary key references auth.users(id) on delete cascade,
    email text not null,
    full_name text,
    avatar_url text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- Enable Row Level Security (RLS)
alter table public.users enable row level security;

-- Policies for public.users
do $$ begin
    if not exists (
        select 1 from pg_policies where tablename = 'users' and policyname = 'Allow read access for authenticated users'
    ) then
        create policy "Allow read access for authenticated users"
            on public.users for select
            to authenticated
            using (true);
    end if;
end $$;

do $$ begin
    if not exists (
        select 1 from pg_policies where tablename = 'users' and policyname = 'Allow user to update own profile'
    ) then
        create policy "Allow user to update own profile"
            on public.users for update
            to authenticated
            using (auth.uid() = id);
    end if;
end $$;

-- Grant access to authenticated and service_role
grant select, update on table public.users to authenticated;
grant all on table public.users to service_role;

-- Function to handle auto-populating public.users when a user registers in auth.users
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer set search_path = public
as $$
begin
  insert into public.users (id, email, full_name, avatar_url, created_at, updated_at)
  values (
    new.id,
    new.email,
    coalesce(new.raw_user_meta_data->>'full_name', split_part(new.email, '@', 1)),
    new.raw_user_meta_data->>'avatar_url',
    coalesce(new.created_at, now()),
    now()
  )
  on conflict (id) do update
  set email = excluded.email,
      full_name = coalesce(excluded.full_name, public.users.full_name),
      avatar_url = coalesce(excluded.avatar_url, public.users.avatar_url),
      updated_at = now();
  return new;
end;
$$;

-- Trigger to execute on auth.users insert or update
drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert or update on auth.users
  for each row execute function public.handle_new_user();
