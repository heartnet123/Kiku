create extension if not exists pgcrypto;

create table if not exists public.chat_sessions (
    id uuid primary key default gen_random_uuid(),
    workspace_id uuid not null references public.workspaces(id) on delete cascade,
    user_id uuid not null references public.users(id) on delete cascade default auth.uid(),
    title text not null default 'New Chat',
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists chat_sessions_workspace_user_updated_idx
    on public.chat_sessions (workspace_id, user_id, updated_at desc);

create table if not exists public.chat_messages (
    id uuid primary key default gen_random_uuid(),
    session_id uuid not null references public.chat_sessions(id) on delete cascade,
    workspace_id uuid not null references public.workspaces(id) on delete cascade,
    role text not null check (role in ('user', 'assistant')),
    content text not null check (length(btrim(content)) > 0),
    citations_json jsonb not null default '[]'::jsonb check (jsonb_typeof(citations_json) = 'array'),
    created_at timestamptz not null default now()
);

create index if not exists chat_messages_session_created_idx
    on public.chat_messages (session_id, workspace_id, created_at);

create index if not exists chat_messages_workspace_session_idx
    on public.chat_messages (workspace_id, session_id);

alter table public.chat_sessions enable row level security;
alter table public.chat_messages enable row level security;

revoke all on table public.chat_sessions from anon;
revoke all on table public.chat_messages from anon;
grant all on table public.chat_sessions to authenticated, service_role;
grant all on table public.chat_messages to authenticated, service_role;

comment on table public.chat_sessions is
    'Workspace/user-scoped chat sessions persisted through Supabase.';
comment on table public.chat_messages is
    'Ordered workspace-scoped chat messages persisted through Supabase.';
