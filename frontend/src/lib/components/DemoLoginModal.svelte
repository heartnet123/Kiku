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
	class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
	role="dialog"
	aria-modal="true"
	aria-labelledby="demo-login-title"
>
	<div class="w-full max-w-md bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-2xl text-slate-100">
		<div class="flex items-center gap-3 mb-6">
			<div class="w-10 h-10 rounded-lg bg-indigo-600 flex items-center justify-center font-bold text-lg text-white">
				K
			</div>
			<div>
				<h2 id="demo-login-title" class="text-xl font-bold">Kiku Workspace Identity</h2>
				<p class="text-xs text-slate-400">Sign in to access your team knowledge base</p>
			</div>
		</div>

		{#if errorMessage}
			<div class="mb-4 p-3 bg-red-950/80 border border-red-800 rounded-lg text-red-300 text-xs">
				{errorMessage}
			</div>
		{/if}

		<form onsubmit={handleLogin} class="space-y-4">
			<div>
				<label for="email" class="block text-xs font-medium text-slate-300 mb-1">Email / Username</label>
				<input
					id="email"
					type="email"
					bind:value={email}
					required
					class="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm focus:outline-none focus:border-indigo-500 text-slate-100"
				/>
			</div>

			<div>
				<label for="password" class="block text-xs font-medium text-slate-300 mb-1">Password</label>
				<input
					id="password"
					type="password"
					bind:value={password}
					required
					class="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm focus:outline-none focus:border-indigo-500 text-slate-100"
				/>
			</div>

			<button
				type="submit"
				disabled={isLoading}
				class="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 font-semibold rounded-lg text-sm transition text-white disabled:opacity-50"
			>
				{isLoading ? 'Signing in...' : 'Sign In'}
			</button>
		</form>

		{#if isDemoMode}
			<div class="mt-6 pt-4 border-t border-slate-800">
				<span class="text-xs font-semibold text-slate-400 block mb-2">⚡ 1-Click Demo Personas:</span>
				<div class="space-y-2">
					<button
						type="button"
						onclick={() => selectPreset('admin@acme.com', 'admin123')}
						class="w-full text-left px-3 py-2 bg-slate-800/80 hover:bg-slate-800 border border-slate-700/60 rounded-lg text-xs flex justify-between items-center transition"
					>
						<div>
							<span class="font-medium text-indigo-400">Acme Admin</span>
							<span class="text-slate-400 block text-[10px]">admin@acme.com</span>
						</div>
						<span class="px-1.5 py-0.5 bg-indigo-900/60 text-indigo-300 rounded text-[10px]">ADMIN</span>
					</button>

					<button
						type="button"
						onclick={() => selectPreset('member@acme.com', 'member123')}
						class="w-full text-left px-3 py-2 bg-slate-800/80 hover:bg-slate-800 border border-slate-700/60 rounded-lg text-xs flex justify-between items-center transition"
					>
						<div>
							<span class="font-medium text-emerald-400">Acme Member</span>
							<span class="text-slate-400 block text-[10px]">member@acme.com</span>
						</div>
						<span class="px-1.5 py-0.5 bg-emerald-900/60 text-emerald-300 rounded text-[10px]">MEMBER</span>
					</button>

					<button
						type="button"
						onclick={() => selectPreset('admin@globex.com', 'admin123')}
						class="w-full text-left px-3 py-2 bg-slate-800/80 hover:bg-slate-800 border border-slate-700/60 rounded-lg text-xs flex justify-between items-center transition"
					>
						<div>
							<span class="font-medium text-amber-400">Globex Admin</span>
							<span class="text-slate-400 block text-[10px]">admin@globex.com</span>
						</div>
						<span class="px-1.5 py-0.5 bg-amber-900/60 text-amber-300 rounded text-[10px]">CROSS-TENANT</span>
					</button>
				</div>
			</div>
		{/if}
	</div>
</div>
