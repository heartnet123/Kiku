<script lang="ts">
	import { apiRequest } from '../api/client';
	import { authModalStore, closeLoginModal, rehydrateAuth, setAuthSession } from '../stores/auth';
	import type { WorkspaceItem, UserProfile } from '../stores/workspace';

	// Keep the local mode in sync with authModalStore state.
	let mode = $state<'login' | 'register'>($authModalStore.mode ?? 'login');
	$effect(() => {
		if ($authModalStore.isOpen && $authModalStore.mode) {
			mode = $authModalStore.mode;
		}
	});
	let email = $state(import.meta.env.DEV ? 'admin@acme.com' : '');
	let password = $state(import.meta.env.DEV ? 'admin123' : '');
	let fullName = $state('');
	let errorMessage = $state('');
	let infoMessage = $state('');
	let isLoading = $state(false);

	async function handleSubmit(event?: Event) {
		event?.preventDefault();
		errorMessage = '';
		infoMessage = '';
		isLoading = true;

		try {
			const response = await apiRequest<{
				token: string | null;
				user?: UserProfile;
				workspaces?: WorkspaceItem[];
				requires_email_confirmation?: boolean;
			}>('/api/v1/auth/' + (mode === 'login' ? 'login' : 'register'), {
				method: 'POST',
				body: JSON.stringify(
					mode === 'login' ? { email, password } : { email, password, full_name: fullName }
				)
			});

			if (!response.token) {
				infoMessage = 'Registration successful. Confirm your email, then sign in.';
				mode = 'login';
				password = '';
				return;
			}

			if (response.user) {
				setAuthSession(response.token, response.user, response.workspaces ?? []);
			} else {
				await rehydrateAuth();
			}
		} catch (error: unknown) {
			errorMessage = error instanceof Error ? error.message : 'Authentication failed.';
		} finally {
			isLoading = false;
		}
	}
</script>

<div
	class="fixed inset-0 z-50 flex items-center justify-center bg-overlay p-4 backdrop-blur-sm"
	role="dialog"
	aria-modal="true"
	aria-labelledby="auth-title"
>
	<div
		class="relative w-full max-w-md rounded-xl border border-border bg-surface p-6 text-text shadow-2xl"
	>
		<button
			type="button"
			class="absolute top-4 right-4 rounded-lg p-1 text-muted hover:bg-surface-raised hover:text-heading"
			onclick={closeLoginModal}
			aria-label="Close auth dialog"
		>
			✕
		</button>
		<div class="mb-5 flex items-center gap-3">
			<div
				class="flex h-10 w-10 items-center justify-center rounded-lg bg-primary text-lg font-bold text-primary-fg"
			>
				K
			</div>
			<div>
				<h2 id="auth-title" class="text-xl font-bold text-heading">Kiku Workspace Identity</h2>
				<p class="text-xs text-muted">Sign in or create your workspace account</p>
			</div>
		</div>

		<div
			class="mb-5 grid grid-cols-2 rounded-lg border border-border bg-surface-raised p-1"
			role="tablist"
			aria-label="Authentication mode"
		>
			<button
				type="button"
				class={mode === 'login'
					? 'rounded-md bg-primary px-3 py-2 text-sm font-semibold text-primary-fg'
					: 'rounded-md px-3 py-2 text-sm font-semibold text-muted hover:text-heading'}
				onclick={() => (mode = 'login')}
			>
				Sign in
			</button>
			<button
				type="button"
				class={mode === 'register'
					? 'rounded-md bg-primary px-3 py-2 text-sm font-semibold text-primary-fg'
					: 'rounded-md px-3 py-2 text-sm font-semibold text-muted hover:text-heading'}
				onclick={() => (mode = 'register')}
			>
				Register
			</button>
		</div>

		{#if errorMessage}
			<div
				class="mb-4 rounded-lg border border-destructive-border bg-destructive-soft p-3 text-xs text-destructive-fg"
				role="alert"
			>
				{errorMessage}
			</div>
		{/if}
		{#if infoMessage}
			<div
				class="mb-4 rounded-lg border border-success-border bg-success-soft p-3 text-xs text-success-fg"
			>
				{infoMessage}
			</div>
		{/if}

		<form onsubmit={handleSubmit} class="space-y-4">
			{#if mode === 'register'}
				<div>
					<label for="full-name" class="mb-1 block text-xs font-medium text-text">Full name</label>
					<input
						id="full-name"
						type="text"
						bind:value={fullName}
						required
						autocomplete="name"
						class="w-full rounded-lg border border-border-strong bg-surface-raised px-3 py-2 text-sm text-text focus:border-primary focus:outline-none"
					/>
				</div>
			{/if}
			<div>
				<label for="email" class="mb-1 block text-xs font-medium text-text">Email</label>
				<input
					id="email"
					type="email"
					bind:value={email}
					required
					autocomplete="email"
					class="w-full rounded-lg border border-border-strong bg-surface-raised px-3 py-2 text-sm text-text focus:border-primary focus:outline-none"
				/>
			</div>
			<div>
				<label for="password" class="mb-1 block text-xs font-medium text-text">Password</label>
				<input
					id="password"
					type="password"
					bind:value={password}
					required
					minlength={mode === 'register' ? 8 : undefined}
					autocomplete={mode === 'register' ? 'new-password' : 'current-password'}
					class="w-full rounded-lg border border-border-strong bg-surface-raised px-3 py-2 text-sm text-text focus:border-primary focus:outline-none"
				/>
			</div>
			<button
				type="submit"
				disabled={isLoading}
				class="w-full rounded-lg bg-primary py-2.5 text-sm font-semibold text-primary-fg transition hover:bg-primary-hover disabled:opacity-50"
			>
				{isLoading ? 'Please wait...' : mode === 'login' ? 'Sign in' : 'Create account'}
			</button>
		</form>
	</div>
</div>
