<script lang="ts">
	import { createWorkspace } from '$lib/features/workspaces/api';
	import { addWorkspace } from '$lib/stores/workspace';

	let name = $state('');
	let slug = $state('');
	let isSubmitting = $state(false);
	let errorMessage = $state<string | null>(null);

	async function handleSubmit(event: SubmitEvent) {
		event.preventDefault();
		if (isSubmitting) return;

		const trimmedName = name.trim();
		if (!trimmedName) {
			errorMessage = 'Workspace name is required.';
			return;
		}

		// Only rendered for an authenticated user with no workspace; the backend
		// rejects unauthenticated creates anyway.
		isSubmitting = true;
		errorMessage = null;

		try {
			const workspace = await createWorkspace(trimmedName, slug.trim() || undefined);
			addWorkspace(workspace);
		} catch (err: unknown) {
			errorMessage = err instanceof Error ? err.message : 'Failed to create workspace.';
		} finally {
			isSubmitting = false;
		}
	}
</script>

<div class="flex min-h-[60vh] flex-col items-center justify-center p-6">
	<div class="w-full max-w-md space-y-6 rounded-2xl border border-border bg-surface p-8 shadow-lg">
		<div class="text-center">
			<div
				class="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-2xl border border-border bg-accent-soft text-accent"
			>
				<svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5m0 0h4m-4 0V9a2 2 0 012-2h2a2 2 0 012 2v12"
					/>
				</svg>
			</div>
			<h2 class="text-2xl font-bold tracking-tight text-heading">Welcome to Kiku</h2>
			<p class="mt-1 text-sm text-muted">
				Create your first workspace to get started with knowledge sources and chat.
			</p>
		</div>

		{#if errorMessage}
			<div
				class="rounded-xl border border-destructive-border bg-destructive-soft p-3 text-xs text-destructive-fg"
			>
				{errorMessage}
			</div>
		{/if}

		<form onsubmit={handleSubmit} class="space-y-4">
			<div>
				<label for="workspace-name" class="mb-1 block text-xs font-semibold text-text"
					>Workspace Name *</label
				>
				<input
					id="workspace-name"
					type="text"
					bind:value={name}
					placeholder="Acme Team, My Project..."
					required
					disabled={isSubmitting}
					class="w-full rounded-xl border border-border bg-surface-raised px-4 py-2.5 text-sm text-text focus:border-accent focus:outline-none disabled:opacity-50"
				/>
			</div>

			<div>
				<label for="workspace-slug" class="mb-1 block text-xs font-semibold text-text"
					>Custom Slug (Optional)</label
				>
				<input
					id="workspace-slug"
					type="text"
					bind:value={slug}
					placeholder="my-workspace"
					disabled={isSubmitting}
					class="w-full rounded-xl border border-border bg-surface-raised px-4 py-2.5 text-sm text-text focus:border-accent focus:outline-none disabled:opacity-50"
				/>
				<p class="mt-1 text-[11px] text-muted">
					Leave empty to auto-generate a unique URL-friendly slug.
				</p>
			</div>

			<button
				type="submit"
				disabled={isSubmitting || !name.trim()}
				class="w-full rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-primary-fg shadow-md transition hover:bg-primary-hover disabled:opacity-50"
			>
				{isSubmitting ? 'Creating Workspace...' : 'Create Workspace'}
			</button>
		</form>
	</div>
</div>
