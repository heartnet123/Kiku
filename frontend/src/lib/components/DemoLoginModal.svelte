<script lang="ts">
	import { apiRequest } from '../api/client';
	import { setAuthSession, type UserProfile, type WorkspaceItem } from '../stores/workspace';

	const isDemoMode = import.meta.env.DEV || import.meta.env.VITE_ENABLE_DEMO === 'true';

	let email = $state(isDemoMode ? 'admin@acme.com' : '');
	let password = $state(isDemoMode ? 'admin123' : '');
	let errorMessage = $state('');
	let isLoading = $state(false);

	interface LoginResponse {
		token: string;
		user: UserProfile;
		workspaces: WorkspaceItem[];
	}

	async function handleLogin(e?: Event) {
		if (e) e.preventDefault();
		errorMessage = '';
		isLoading = true;

		try {
			const res = await apiRequest<LoginResponse>('/api/v1/auth/login', {
				method: 'POST',
				body: JSON.stringify({ email, password })
			});
			setAuthSession(res.token, res.user, res.workspaces);
		} catch (err: any) {
			errorMessage = err?.message || 'Login failed. Check credentials.';
		} finally {
			isLoading = false;
		}
	}

	function selectPreset(presetEmail: string, presetPass: string) {
		email = presetEmail;
		password = presetPass;
		handleLogin();
	}
</script>

<div
	class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm"
	role="dialog"
	aria-modal="true"
	aria-labelledby="demo-login-title"
>
	<div
		class="w-full max-w-md rounded-xl border border-slate-800 bg-slate-900 p-6 text-slate-100 shadow-2xl"
	>
		<div class="mb-6 flex items-center gap-3">
			<div
				class="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-600 text-lg font-bold text-white"
			>
				K
			</div>
			<div>
				<h2 id="demo-login-title" class="text-xl font-bold">Kiku Workspace Identity</h2>
				<p class="text-xs text-slate-400">Sign in to access your team knowledge base</p>
			</div>
		</div>

		{#if errorMessage}
			<div class="mb-4 rounded-lg border border-red-800 bg-red-950/80 p-3 text-xs text-red-300">
				{errorMessage}
			</div>
		{/if}

		<form onsubmit={handleLogin} class="space-y-4">
			<div>
				<label for="email" class="mb-1 block text-xs font-medium text-slate-300"
					>Email / Username</label
				>
				<input
					id="email"
					type="email"
					bind:value={email}
					required
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
					class="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-100 focus:border-indigo-500 focus:outline-none"
				/>
			</div>

			<button
				type="submit"
				disabled={isLoading}
				class="w-full rounded-lg bg-indigo-600 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:opacity-50"
			>
				{isLoading ? 'Signing in...' : 'Sign In'}
			</button>
		</form>

		{#if isDemoMode}
			<div class="mt-6 border-t border-slate-800 pt-4">
				<span class="mb-2 block text-xs font-semibold text-slate-400"
					>⚡ 1-Click Demo Personas:</span
				>
				<div class="space-y-2">
					<button
						type="button"
						onclick={() => selectPreset('admin@acme.com', 'admin123')}
						class="flex w-full items-center justify-between rounded-lg border border-slate-700/60 bg-slate-800/80 px-3 py-2 text-left text-xs transition hover:bg-slate-800"
					>
						<div>
							<span class="font-medium text-indigo-400">Acme Admin</span>
							<span class="block text-[10px] text-slate-400">admin@acme.com</span>
						</div>
						<span class="rounded bg-indigo-900/60 px-1.5 py-0.5 text-[10px] text-indigo-300"
							>ADMIN</span
						>
					</button>

					<button
						type="button"
						onclick={() => selectPreset('member@acme.com', 'member123')}
						class="flex w-full items-center justify-between rounded-lg border border-slate-700/60 bg-slate-800/80 px-3 py-2 text-left text-xs transition hover:bg-slate-800"
					>
						<div>
							<span class="font-medium text-emerald-400">Acme Member</span>
							<span class="block text-[10px] text-slate-400">member@acme.com</span>
						</div>
						<span class="rounded bg-emerald-900/60 px-1.5 py-0.5 text-[10px] text-emerald-300"
							>MEMBER</span
						>
					</button>

					<button
						type="button"
						onclick={() => selectPreset('admin@globex.com', 'admin123')}
						class="flex w-full items-center justify-between rounded-lg border border-slate-700/60 bg-slate-800/80 px-3 py-2 text-left text-xs transition hover:bg-slate-800"
					>
						<div>
							<span class="font-medium text-amber-400">Globex Admin</span>
							<span class="block text-[10px] text-slate-400">admin@globex.com</span>
						</div>
						<span class="rounded bg-amber-900/60 px-1.5 py-0.5 text-[10px] text-amber-300"
							>CROSS-TENANT</span
						>
					</button>
				</div>
			</div>
		{/if}
	</div>
</div>
