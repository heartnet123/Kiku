<script lang="ts">
	import { workspaceStore, getCurrentWorkspaceId } from '$lib/stores/workspace';
	import { authStore, openLoginModal, openRegisterModal, requireAuth } from '$lib/stores/auth';
	import { fetchSourceMetrics, fetchWorkspaceSources } from '$lib/features/sources/api';
	import type { IngestionMetrics, SourceItem } from '$lib/features/sources/types';
	import SourcesList from '$lib/features/sources/SourcesList.svelte';
	import SourceUploadModal from '$lib/features/sources/SourceUploadModal.svelte';
	import WorkspaceOnboarding from '$lib/components/WorkspaceOnboarding.svelte';

	let isAuthenticated = $derived($authStore.isAuthenticated);
	let isRehydrating = $derived($authStore.isRehydrating);
	let workspaceId = $derived($workspaceStore.currentWorkspace?.id || getCurrentWorkspaceId());
	let hasNoWorkspace = $derived(isAuthenticated && !isRehydrating && !workspaceId);

	let sources = $state<SourceItem[]>([]);
	let metrics = $state<IngestionMetrics | null>(null);
	let isLoading = $state(false);
	let errorMessage = $state<string | null>(null);
	let isUploadModalOpen = $state(false);

	$effect(() => {
		if (!isRehydrating && isAuthenticated && workspaceId) {
			loadData(workspaceId);
		} else if (!isRehydrating && (!isAuthenticated || !workspaceId)) {
			isLoading = false;
			sources = [];
			metrics = null;
		}
	});

	async function loadData(targetWorkspaceId?: string) {
		const activeId = targetWorkspaceId || workspaceId || getCurrentWorkspaceId();
		if (!isAuthenticated || !activeId) {
			isLoading = false;
			sources = [];
			metrics = null;
			return;
		}

		isLoading = true;
		errorMessage = null;
		try {
			const [sourcesRes, metricsRes] = await Promise.all([
				fetchWorkspaceSources(activeId).catch(() => []),
				fetchSourceMetrics(activeId).catch(() => null)
			]);
			sources = sourcesRes;
			metrics = metricsRes;
		} catch (err: unknown) {
			errorMessage = err instanceof Error ? err.message : 'Failed to load knowledge sources.';
		} finally {
			isLoading = false;
		}
	}

	function handleAddSource() {
		requireAuth(() => {
			isUploadModalOpen = true;
		});
	}
</script>

<div class="min-h-screen bg-bg p-6 text-text md:p-10">
	<div class="mx-auto max-w-6xl space-y-8">
		{#if isRehydrating}
			<div class="flex items-center justify-center py-20">
				<div class="flex flex-col items-center gap-3 text-muted">
					<svg class="h-8 w-8 animate-spin text-accent" fill="none" viewBox="0 0 24 24">
						<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
						<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
					</svg>
					<span class="text-sm font-medium">Checking workspace authentication...</span>
				</div>
			</div>
		{:else if !isAuthenticated}
			<div class="flex flex-col items-center justify-center rounded-2xl border border-border bg-surface p-12 text-center shadow-sm">
				<div class="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl border border-border bg-accent-soft text-accent">
					<svg class="h-7 w-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
					</svg>
				</div>
				<h3 class="text-xl font-bold text-heading">Authentication Required</h3>
				<p class="mt-2 max-w-md text-sm text-muted">Please log in to view workspace sources.</p>
				<div class="mt-6 flex items-center justify-center gap-3">
					<button onclick={() => openLoginModal()} class="rounded-xl bg-primary px-5 py-2.5 text-sm font-semibold text-primary-fg shadow-md transition hover:bg-primary-hover">
						Log in
					</button>
					<button onclick={() => openRegisterModal()} class="rounded-xl border border-border bg-surface-raised px-5 py-2.5 text-sm font-semibold text-text transition hover:bg-surface-raised/80 hover:text-heading">
						Register
					</button>
				</div>
			</div>
		{:else if hasNoWorkspace}
			<WorkspaceOnboarding />
		{:else}
			<!-- Header -->
			<div class="flex flex-col justify-between gap-4 border-b border-border pb-6 sm:flex-row sm:items-center">
				<div>
					<div class="flex items-center gap-3">
						<div class="rounded-xl border border-border bg-accent-soft p-2.5 text-accent">
							<svg class="h-7 w-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 01-2-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
							</svg>
						</div>
						<div>
							<h1 class="text-3xl font-extrabold tracking-tight text-heading">Knowledge Sources</h1>
							<p class="mt-0.5 text-sm text-muted">
								Workspace-scoped LlamaIndex ingestion pipeline & Supabase vector store management.
							</p>
						</div>
					</div>
				</div>

				<div class="flex items-center gap-3">
					<button
						onclick={() => loadData()}
						disabled={isLoading}
						class="flex items-center gap-2 rounded-xl border border-border bg-surface px-4 py-2.5 text-sm font-semibold text-text transition hover:bg-surface-raised hover:text-heading disabled:opacity-50"
					>
						<svg class={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
						</svg>
						Refresh
					</button>
					<button
						onclick={handleAddSource}
						class="flex items-center gap-2 rounded-xl bg-primary px-5 py-2.5 text-sm font-semibold text-primary-fg shadow-lg transition hover:bg-primary-hover"
					>
						<svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
						</svg>
						Add Source
					</button>
				</div>
			</div>

			{#if errorMessage}
				<div class="rounded-xl border border-destructive-border bg-destructive-soft p-4 text-sm text-destructive-fg">
					{errorMessage}
				</div>
			{/if}

			{#if isLoading && sources.length === 0}
				<div class="flex items-center justify-center py-20">
					<div class="flex flex-col items-center gap-3 text-muted">
						<svg class="h-8 w-8 animate-spin text-accent" fill="none" viewBox="0 0 24 24">
							<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
							<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
						</svg>
						<span class="text-sm font-medium">Loading workspace sources...</span>
					</div>
				</div>
			{:else}
				<SourcesList {workspaceId} {sources} {metrics} onRefresh={loadData} />
			{/if}
		{/if}
	</div>

	<!-- Upload Modal -->
	<SourceUploadModal
		{workspaceId}
		isOpen={isUploadModalOpen}
		onClose={() => (isUploadModalOpen = false)}
		onUploaded={() => {
			loadData();
		}}
	/>
</div>
