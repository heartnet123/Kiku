<script lang="ts">
	import { apiRequest } from '../api/client';
	import { setAuthSession, type UserProfile, type WorkspaceItem } from '../stores/workspace';

	const isDemoMode = import.meta.env.DEV || import.meta.env.VITE_ENABLE_DEMO === 'true';

	let mode = $state<'login' | 'register'>('login');
	let email = $state(isDemoMode ? 'admin@acme.com' : '');
	let password = $state(isDemoMode ? 'admin123' : '');
	let fullName = $state('');
	let errorMessage = $state('');
	let infoMessage = $state('');
	let isLoading = $state(false);

	interface AuthResponse {
		token: string | null;
		refresh_token?: string | null;
		user: UserProfile;
		workspaces: WorkspaceItem[];
		requires_email_confirmation?: boolean;
	}

	async function handleSubmit(event?: Event) {
		event?.preventDefault();
		errorMessage = '';
		infoMessage = '';
		isLoading = true;

		try {
			const response = await apiRequest<AuthResponse>(
				'/api/v1/auth/' + (mode === 'login' ? 'login' : 'register'),
				{
					method: 'POST',
					body: JSON.stringify(
						mode === 'login' ? { email, password } : { email, password, full_name: fullName }
					)
				}
			);
			if (!response.token) {
				infoMessage = 'Registration successful. Confirm your email, then sign in.';
				mode = 'login';
				password = '';
				return;
			}
			setAuthSession(
				response.token,
				response.user,
				response.workspaces,
				response.refresh_token ?? null
			);
		} catch (error: unknown) {
			errorMessage = error instanceof Error ? error.message : 'Authentication failed.';
		} finally {
			isLoading = false;
		}
	}

	function selectPreset(presetEmail: string, presetPassword: string) {
		mode = 'login';
		email = presetEmail;
		password = presetPassword;
		void handleSubmit();
	}
</script>

<div
	class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm"
	role="dialog"
	aria-modal="true"
	aria-labelledby="auth-title"
>
	<div
		class="w-full max-w-md rounded-xl border border-slate-800 bg-slate-900 p-6 text-slate-100 shadow-2xl"
	>
		<div class="mb-5 flex items-center gap-3">
			<div
				class="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-600 text-lg font-bold text-white"
			>
				K
			</div>
			<div>
				<h2 id="auth-title" class="text-xl font-bold">Kiku Workspace Identity</h2>
				<p class="text-xs text-slate-400">Sign in or create your workspace account</p>
			</div>
		</div>

		<div
			class="mb-5 grid grid-cols-2 rounded-lg bg-slate-800 p-1"
			role="tablist"
			aria-label="Authentication mode"
		>
			<button
				type="button"
				class={mode === 'login'
					? 'rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white'
					: 'rounded-md px-3 py-2 text-sm font-semibold text-slate-300'}
				onclick={() => (mode = 'login')}
			>
				Sign in
			</button>
			<button
				type="button"
				class={mode === 'register'
					? 'rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white'
					: 'rounded-md px-3 py-2 text-sm font-semibold text-slate-300'}
				onclick={() => (mode = 'register')}
			>
				Register
			</button>
		</div>

		{#if errorMessage}
			<div
				class="mb-4 rounded-lg border border-red-800 bg-red-950/80 p-3 text-xs text-red-300"
				role="alert"
			>
				{errorMessage}
			</div>
		{/if}
		{#if infoMessage}
			<div
				class="mb-4 rounded-lg border border-emerald-800 bg-emerald-950/60 p-3 text-xs text-emerald-300"
			>
				{infoMessage}
			</div>
		{/if}

		<form onsubmit={handleSubmit} class="space-y-4">
			{#if mode === 'register'}
				<div>
					<label for="full-name" class="mb-1 block text-xs font-medium text-slate-300"
						>Full name</label
					>
					<input
						id="full-name"
						type="text"
						bind:value={fullName}
						required
						autocomplete="name"
						class="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-100 focus:border-indigo-500 focus:outline-none"
					/>
				</div>
			{/if}
			<div>
				<label for="email" class="mb-1 block text-xs font-medium text-slate-300">Email</label>
				<input
					id="email"
					type="email"
					bind:value={email}
					required
					autocomplete="email"
					class="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-100 focus:border-indigo-500 focus:outline-none"
				/>
			</div>
			<div>
				<label for="password" class="mb-1 block text-xs font-medium text-slate-300">Password</label>
				<input
					id="password"
					type="password"
					bind:value={password}
					required
					minlength={mode === 'register' ? 8 : undefined}
					autocomplete={mode === 'register' ? 'new-password' : 'current-password'}
					class="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-100 focus:border-indigo-500 focus:outline-none"
				/>
			</div>
			<button
				type="submit"
				disabled={isLoading}
				class="w-full rounded-lg bg-indigo-600 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:opacity-50"
			>
				{isLoading ? 'Please wait...' : mode === 'login' ? 'Sign in' : 'Create account'}
			</button>
		</form>

		{#if isDemoMode && mode === 'login'}
			<div class="mt-6 border-t border-slate-800 pt-4">
				<span class="mb-2 block text-xs font-semibold text-slate-400">1-click demo personas</span>
				<div class="space-y-2">
					<button
						type="button"
						onclick={() => selectPreset('admin@acme.com', 'admin123')}
						class="flex w-full items-center justify-between rounded-lg border border-slate-700/60 bg-slate-800/80 px-3 py-2 text-left text-xs transition hover:bg-slate-800"
					>
						<span
							><span class="font-medium text-indigo-400">Acme Admin</span><span
								class="block text-[10px] text-slate-400">admin@acme.com</span
							></span
						>
						<span class="rounded bg-indigo-900/60 px-1.5 py-0.5 text-[10px] text-indigo-300"
							>ADMIN</span
						>
					</button>
					<button
						type="button"
						onclick={() => selectPreset('member@acme.com', 'member123')}
						class="flex w-full items-center justify-between rounded-lg border border-slate-700/60 bg-slate-800/80 px-3 py-2 text-left text-xs transition hover:bg-slate-800"
					>
						<span
							><span class="font-medium text-emerald-400">Acme Member</span><span
								class="block text-[10px] text-slate-400">member@acme.com</span
							></span
						>
						<span class="rounded bg-emerald-900/60 px-1.5 py-0.5 text-[10px] text-emerald-300"
							>MEMBER</span
						>
					</button>
					<button
						type="button"
						onclick={() => selectPreset('admin@globex.com', 'admin123')}
						class="flex w-full items-center justify-between rounded-lg border border-slate-700/60 bg-slate-800/80 px-3 py-2 text-left text-xs transition hover:bg-slate-800"
					>
						<span
							><span class="font-medium text-amber-400">Globex Admin</span><span
								class="block text-[10px] text-slate-400">admin@globex.com</span
							></span
						>
						<span class="rounded bg-amber-900/60 px-1.5 py-0.5 text-[10px] text-amber-300"
							>CROSS-TENANT</span
						>
					</button>
				</div>
			</div>
		{/if}
	</div>
</div>
