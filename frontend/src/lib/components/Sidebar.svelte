<script lang="ts">
	import { page } from '$app/state';
	import { resolve } from '$app/paths';
	import Icon, { type IconName } from '$lib/components/Icon.svelte';
	import KikuMascot from '$lib/components/KikuMascot.svelte';

	type AppRoute = Parameters<typeof resolve>[0];
	const navItems: { label: string; href: AppRoute; icon: IconName }[] = [
		{ label: 'Home', href: '/', icon: 'home' },
		{ label: 'FAQs', href: '/faqs', icon: 'help' },
		{ label: 'Sources', href: '/sources', icon: 'document' },
		{ label: 'Analytics', href: '/analytics', icon: 'chart' },
		{ label: 'Settings', href: '/settings', icon: 'settings' }
	];
</script>

<aside class="sidebar" aria-label="Main navigation">
	<div class="sidebar-top">
		<a class="brand" href={resolve('/')} aria-label="Kiku home">
			<img class="brand-icon" src="/kiku-icon.png" alt="" aria-hidden="true" />
			<span>Kiku</span>
		</a>
		<nav class="primary-nav">
			{#each navItems as item (item.href)}
				{@const isActive = page.url.pathname === item.href}
				<a
					class="nav-item"
					class:active={isActive}
					href={resolve(item.href)}
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
	</div>

	<button class="team-switcher" type="button" aria-label="Switch team">
		<span class="team-icon"><Icon name="users" size={20} /></span>
		<span class="team-copy"><strong>Acme Team</strong><small>Pro Plan</small></span>
		<Icon name="chevron-down" size={16} className="team-chevron" />
	</button>
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
