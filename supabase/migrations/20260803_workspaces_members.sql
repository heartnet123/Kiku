-- Create extension if not exists
create extension if not exists pgcrypto;

-- Workspaces table
create table if not exists public.workspaces (
    id uuid primary key default gen_random_uuid(),
    name text not null check (length(btrim(name)) > 0),
    slug text not null unique check (length(btrim(slug)) > 0),
    owner_id uuid references public.users(id) on delete set null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists workspaces_slug_idx on public.workspaces (slug);

-- Workspace members table
create table if not exists public.workspace_members (
    id uuid primary key default gen_random_uuid(),
    workspace_id uuid not null references public.workspaces(id) on delete cascade,
    user_id uuid not null references public.users(id) on delete cascade,
    role text not null check (role in ('owner', 'admin', 'editor', 'viewer', 'member')),
    created_at timestamptz not null default now(),
    unique (workspace_id, user_id)
);

create index if not exists workspace_members_user_idx on public.workspace_members (user_id);
create index if not exists workspace_members_workspace_idx on public.workspace_members (workspace_id);

-- Enable Row Level Security
alter table public.workspaces enable row level security;
alter table public.workspace_members enable row level security;

-- Grant permissions
grant select, insert, update on table public.workspaces to authenticated;
grant select, insert, update, delete on table public.workspace_members to authenticated;
grant all on table public.workspaces to service_role;
grant all on table public.workspace_members to service_role;
