<script lang="ts">
	import { createWorkspace, joinWorkspace } from '$lib/features/workspaces/api';
	import { addWorkspace } from '$lib/stores/workspace';
	import { requireAuth } from '$lib/stores/auth';

	let mode = $state<'create' | 'join' | null>(null);
	let name = $state('');
	let slug = $state('');
	let identifier = $state('');
	let errorMessage = $state('');
	let isLoading = $state(false);

	function setMode(targetMode: 'create' | 'join') {
		requireAuth(() => {
			mode = targetMode;
		});
	}

	async function submit(event: SubmitEvent) {
		event.preventDefault();
		requireAuth(async () => {
			errorMessage = '';
			isLoading = true;
			try {
				const workspace =
					mode === 'create' ? await createWorkspace(name, slug) : await joinWorkspace(identifier);
				addWorkspace(workspace);
				mode = null;
				name = '';
				slug = '';
				identifier = '';
			} catch (error: unknown) {
				errorMessage = error instanceof Error ? error.message : 'Workspace action failed.';
			} finally {
				isLoading = false;
			}
		});
	}
</script>

<div class="workspace-actions">
	<div class="workspace-action-buttons">
		<button type="button" class="workspace-action" onclick={() => setMode('create')}
			>+ Create workspace</button
		>
		<button type="button" class="workspace-action" onclick={() => setMode('join')}
			>Join workspace</button
		>
	</div>

	{#if mode}
		<form onsubmit={submit} class="workspace-form">
			<strong>{mode === 'create' ? 'Create workspace' : 'Join workspace'}</strong>
			{#if mode === 'create'}
				<input
					bind:value={name}
					required
					maxlength="120"
					placeholder="Workspace name"
					aria-label="Workspace name"
				/>
				<input
					bind:value={slug}
					maxlength="64"
					placeholder="Slug (optional)"
					aria-label="Workspace slug"
				/>
			{:else}
				<input
					bind:value={identifier}
					required
					placeholder="Workspace slug or ID"
					aria-label="Workspace slug or ID"
				/>
			{/if}
			{#if errorMessage}<small class="workspace-error" role="alert">{errorMessage}</small>{/if}
			<div class="workspace-form-actions">
				<button type="button" class="workspace-cancel" onclick={() => (mode = null)}>Cancel</button>
				<button type="submit" class="workspace-submit" disabled={isLoading}
					>{isLoading ? 'Saving...' : 'Continue'}</button
				>
			</div>
		</form>
	{/if}
</div>

<style>
	.workspace-actions {
		border-top: 1px solid #332d4d;
		margin: 4px 0;
		padding: 6px 0;
	}
	.workspace-action-buttons {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 4px;
	}
	.workspace-action,
	.workspace-cancel,
	.workspace-submit {
		border: 0;
		border-radius: 6px;
		cursor: pointer;
		font-size: 10px;
		padding: 7px 6px;
	}
	.workspace-action {
		background: #2a2540;
		color: #c4b5fd;
	}
	.workspace-action:hover {
		background: #3b2d66;
	}
	.workspace-form {
		display: grid;
		gap: 6px;
		margin-top: 6px;
	}
	.workspace-form strong {
		color: #e2e8f0;
		font-size: 11px;
	}
	.workspace-form input {
		width: 100%;
		border: 1px solid #4c4568;
		border-radius: 6px;
		background: #161326;
		color: #f8fafc;
		font-size: 11px;
		padding: 7px;
	}
	.workspace-form-actions {
		display: flex;
		justify-content: flex-end;
		gap: 5px;
	}
	.workspace-cancel {
		background: transparent;
		color: #94a3b8;
	}
	.workspace-submit {
		background: #7c5bd6;
		color: white;
	}
	.workspace-submit:disabled {
		opacity: 0.5;
	}
	.workspace-error {
		color: #fca5a5;
		font-size: 10px;
	}
</style>
