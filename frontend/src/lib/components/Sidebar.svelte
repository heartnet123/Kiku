	<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import Icon, { type IconName } from '$lib/components/Icon.svelte';
	import KikuMascot from '$lib/components/KikuMascot.svelte';
	import WorkspaceActions from './WorkspaceActions.svelte';
	import { authStore, logout, switchWorkspace } from '../stores/workspace';

	import { listSessions, deleteSession } from '$lib/features/chat/chatApi';
	import type { ChatSession } from '$lib/features/chat/types';

	const navItems: { label: string; href: string; icon: IconName }[] = [
		{ label: 'Home', href: '/', icon: 'home' },
		{ label: 'FAQs', href: '/faqs', icon: 'help' },
		{ label: 'Sources', href: '/sources', icon: 'document' },
		{ label: 'Analytics', href: '/analytics', icon: 'chart' },
		{ label: 'Settings', href: '/settings', icon: 'settings' }
	];

	let isDropdownOpen = $state(false);
	let sessions = $state<ChatSession[]>([]);

	$effect(() => {
		const isAuthenticated = $authStore.isAuthenticated;
		const workspaceId = $authStore.currentWorkspace?.id;
		if (!isAuthenticated || !workspaceId) {
			sessions = [];
			return;
		}
		void reloadSessions();
	});

	async function reloadSessions() {
		try {
			sessions = await listSessions();
		} catch {}
	}

	async function handleDeleteChat(id: string, event: MouseEvent) {
		event.stopPropagation();
		try {
			await deleteSession(id);
			sessions = sessions.filter((s) => s.id !== id);
			if (page.params.sessionId === id) await goto('/');
		} catch {}
	}

	function toggleDropdown() {
		isDropdownOpen = !isDropdownOpen;
	}
</script>

<aside class="sidebar" aria-label="Main navigation">
	<div class="sidebar-top">
			<a class="brand" href="/" aria-label="Kiku home">
			<img class="brand-icon" src="/kiku-icon.png" alt="" aria-hidden="true" />
			<span>Kiku</span>
		</a>
		<nav class="primary-nav">
			{#each navItems as item (item.href)}
				{@const isActive = page.url.pathname === item.href}
				<a
					class="nav-item"
					class:active={isActive}
						href={item.href}
					aria-current={isActive ? 'page' : undefined}
				>
					<Icon name={item.icon} size={18} />
					<span>{item.label}</span>
				</a>
			{/each}
		</nav>

		<section class="ask-kiku-card" aria-label="Ask Kiku">
			<div class="ask-kiku-copy">
				<strong>Ask Kiku</strong>
				<p>Your AI assistant<br />for instant answers</p>
			</div>
			<div class="mascot-wrap mascot-small"><KikuMascot className="mascot" /></div>
			<span class="card-arrow" aria-hidden="true">›</span>
		</section>

		<section class="chat-sessions-section">
			<div class="sessions-header">
				<span>Recent Chats</span>
				<a class="new-chat-btn" href="/">+ New</a>
			</div>
			<div class="sessions-list">
				{#each sessions as s (s.id)}
					<div class="session-item" class:active={page.params.sessionId === s.id}>
						<a
							class="session-link"
							href={`/chat/${encodeURIComponent(s.id)}`}
							aria-current={page.params.sessionId === s.id ? 'page' : undefined}
						>
							<span class="session-title">{s.title}</span>
						</a>
						<button
							type="button"
							class="delete-chat-btn"
							aria-label={`Delete chat ${s.title}`}
							onclick={(event) => handleDeleteChat(s.id, event)}
						>
							✕
						</button>
					</div>
				{/each}
			</div>
		</section>
	</div>

	<div class="team-switcher-container">
		{#if isDropdownOpen && $authStore.isAuthenticated}
			<div class="workspace-dropdown">
				<div class="dropdown-header">Workspaces</div>
				{#each $authStore.workspaces as ws}
					<button
						type="button"
						class="dropdown-item"
						class:active={ws.id === $authStore.currentWorkspace?.id}
						onclick={() => {
							switchWorkspace(ws.id);
							isDropdownOpen = false;
						}}
					>
						<span>{ws.name}</span>
						<span class="role-badge">{ws.role.toUpperCase()}</span>
					</button>
				{/each}
				<WorkspaceActions />
				<button
					type="button"
					class="dropdown-item logout-item"
					onclick={() => {
						logout();
						isDropdownOpen = false;
					}}
				>
					<span>Sign Out / Switch Persona</span>
				</button>
			</div>
		{/if}

		<button class="team-switcher" type="button" onclick={toggleDropdown} aria-label="Switch team">
			<span class="team-icon"><Icon name="users" size={20} /></span>
			<span class="team-copy">
				<strong>{$authStore.currentWorkspace?.name ?? 'Sign In Required'}</strong>
				<small
					>{$authStore.user
						? `${$authStore.user.full_name} (${$authStore.currentWorkspace?.role?.toUpperCase() || 'GUEST'})`
						: 'Click to sign in'}</small
				>
			</span>
			<Icon name="chevron-down" size={16} className="team-chevron" />
		</button>
	</div>
</aside>

<style>
	.sidebar {
		position: sticky;
		top: 0;
		display: flex;
		width: 248px;
		height: calc(100vh / var(--ui-scale));
		flex: 0 0 248px;
		flex-direction: column;
		justify-content: space-between;
		border-right: 1px solid var(--color-border);
		background: var(--color-surface);
	}
	.sidebar-top {
		padding: 21px 15px 0;
	}
	.brand {
		display: inline-flex;
		align-items: center;
		gap: 8px;
		margin: 0 11px 23px;
		color: var(--color-heading);
		font-size: 26px;
		font-weight: 600;
		letter-spacing: -1.2px;
		line-height: 1;
		text-decoration: none;
	}
	.brand-icon {
		width: 52px;
		height: 52px;
		border-radius: var(--radius-control);
		object-fit: cover;
	}
	.primary-nav {
		display: grid;
		gap: 5px;
	}
	.nav-item {
		display: flex;
		width: 100%;
		min-height: 39px;
		align-items: center;
		gap: 13px;
		padding: 8px 12px;
		border-radius: var(--radius-control);
		color: var(--color-muted);
		font-size: 14px;
		font-weight: 600;
		text-decoration: none;
		transition:
			background 150ms ease,
			color 150ms ease,
			transform 150ms ease;
	}
	.nav-item:hover {
		background: var(--color-surface-raised);
		color: var(--color-text);
	}
	.nav-item:active {
		transform: scale(0.985);
	}
	.nav-item.active {
		background: #eee6ff;
		color: var(--color-accent);
	}
	.ask-kiku-card {
		position: relative;
		display: flex;
		min-height: 108px;
		align-items: flex-start;
		margin-top: 39px;
		padding: 14px;
		overflow: hidden;
		border: 1px solid #eadffd;
		border-radius: var(--radius-card);
		background: linear-gradient(135deg, #faf6ff, #f5eeff);
	}
	.ask-kiku-copy {
		position: relative;
		z-index: 1;
		margin-left: 62px;
	}
	.ask-kiku-copy strong {
		display: block;
		margin-top: 1px;
		color: var(--color-heading);
		font-size: 12px;
		font-weight: 600;
	}
	.ask-kiku-copy p {
		margin: 7px 0 0;
		color: var(--color-subtle);
		font-size: 10px;
		line-height: 1.45;
	}
	.mascot-wrap {
		position: absolute;
		bottom: 5px;
		left: 8px;
	}
	.mascot-small {
		width: 64px;
		height: 64px;
	}
	:global(.mascot) {
		display: block;
		width: 100%;
		height: 100%;
	}
	.card-arrow {
		position: absolute;
		right: 13px;
		bottom: 12px;
		color: var(--color-accent);
		font-size: 26px;
		line-height: 0.6;
	}
	.team-switcher-container {
		position: relative;
	}
	.workspace-dropdown {
		position: absolute;
		bottom: 100%;
		left: 0;
		right: 0;
		margin-bottom: 4px;
		background: #1e1b2e;
		border: 1px solid #332d4d;
		border-radius: var(--radius-card);
		padding: 6px;
		z-index: 30;
		box-shadow: 0 -4px 16px rgba(0, 0, 0, 0.3);
	}
	.dropdown-header {
		padding: 4px 8px;
		font-size: 10px;
		font-weight: 700;
		color: #94a3b8;
		text-transform: uppercase;
	}
	.dropdown-item {
		width: 100%;
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 8px;
		background: transparent;
		border: 0;
		border-radius: var(--radius-control);
		color: #e2e8f0;
		font-size: 12px;
		cursor: pointer;
		text-align: left;
	}
	.dropdown-item:hover {
		background: #2a2540;
	}
	.dropdown-item.active {
		background: #3b2d66;
		font-weight: 600;
	}
	.role-badge {
		font-size: 9px;
		padding: 2px 6px;
		border-radius: 4px;
		background: #475569;
		color: #f8fafc;
	}
	.logout-item {
		border-top: 1px solid #332d4d;
		margin-top: 4px;
		color: #f87171;
	}
	.team-switcher {
		display: flex;
		width: 100%;
		min-height: 77px;
		align-items: center;
		gap: 10px;
		padding: 14px 19px;
		border: 0;
		border-top: 1px solid var(--color-border);
		background: var(--color-surface);
		color: var(--color-heading);
		cursor: pointer;
		text-align: left;
	}
	.team-icon {
		display: grid;
		width: 36px;
		height: 36px;
		flex: 0 0 36px;
		place-items: center;
		border-radius: var(--radius-control);
		background: #eee6ff;
		color: var(--color-accent);
	}
	.team-copy {
		display: grid;
		gap: 3px;
		min-width: 0;
	}
	.team-copy strong {
		font-size: 12px;
		font-weight: 600;
	}
	.team-copy small {
		color: var(--color-muted);
		font-size: 11px;
	}
	:global(.team-chevron) {
		margin-left: auto;
		color: var(--color-muted);
	}
	.chat-sessions-section {
		margin-top: 16px;
	}
	.sessions-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 4px 8px;
		font-size: 11px;
		font-weight: 600;
		color: var(--color-muted);
		text-transform: uppercase;
	}
	.new-chat-btn {
		display: inline-flex;
		align-items: center;
		background: transparent;
		border: 1px solid var(--color-accent);
		color: var(--color-accent);
		padding: 2px 8px;
		border-radius: 4px;
		font-size: 10px;
		font-weight: 600;
		text-decoration: none;
	}
	.sessions-list {
		display: flex;
		flex-direction: column;
		gap: 4px;
		margin-top: 6px;
		max-height: 180px;
		overflow-y: auto;
	}
	.session-item {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 6px 10px;
		border-radius: var(--radius-control);
		font-size: 12px;
		color: var(--color-text);
		background: var(--color-surface-raised);
		border: 1px solid transparent;
	}
	.session-item.active {
		border-color: #eadffd;
		background: var(--color-surface-soft);
	}
	.session-link {
		min-width: 0;
		flex: 1;
		color: inherit;
		text-decoration: none;
	}
	.session-title {
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		max-width: 170px;
	}
	.delete-chat-btn {
		background: transparent;
		border: none;
		color: #ef4444;
		font-size: 11px;
		cursor: pointer;
		opacity: 0.7;
	}
	.delete-chat-btn:hover {
		opacity: 1;
	}

	@media (max-width: 900px) {
		.sidebar {
			width: 216px;
			flex-basis: 216px;
		}
	}
	@media (max-width: 640px) {
		.sidebar {
			position: relative;
			width: 100%;
			height: auto;
			min-height: 0;
			border-right: 0;
			border-bottom: 1px solid var(--color-border);
		}
		.sidebar-top {
			padding: 17px 16px 14px;
		}
		.brand {
			margin: 0 2px 16px;
		}
		.primary-nav {
			display: flex;
			gap: 5px;
			overflow-x: auto;
			padding-bottom: 2px;
		}
		.nav-item {
			width: auto;
			min-width: max-content;
			padding: 8px 11px;
		}
		.nav-item span {
			font-size: 12px;
		}
		.ask-kiku-card {
			display: none;
		}
		.team-switcher {
			min-height: 61px;
			padding: 10px 16px;
		}
	}
</style>
