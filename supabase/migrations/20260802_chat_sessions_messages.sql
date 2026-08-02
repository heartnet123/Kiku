create extension if not exists pgcrypto;

create table if not exists public.chat_sessions (
    id uuid primary key default gen_random_uuid(),
    workspace_id text not null,
    user_id text not null,
    title text not null default 'New Chat',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists chat_sessions_workspace_user_updated_idx
    on public.chat_sessions (workspace_id, user_id, updated_at desc);

create table if not exists public.chat_messages (
    id uuid primary key default gen_random_uuid(),
    session_id uuid not null references public.chat_sessions(id) on delete cascade,
    workspace_id text not null,
    role text not null check (role in ('user', 'assistant')),
    content text not null,
    citations_json jsonb,
    created_at timestamptz not null default now()
);

create index if not exists chat_messages_session_created_idx
    on public.chat_messages (session_id, created_at);

create index if not exists chat_messages_workspace_session_idx
    on public.chat_messages (workspace_id, session_id);

alter table public.chat_sessions enable row level security;
alter table public.chat_messages enable row level security;

comment on table public.chat_sessions is
    'Workspace/user-scoped chat sessions. Access is through the backend service role.';
comment on table public.chat_messages is
    'Ordered chat messages. Access is through the backend service role.';
