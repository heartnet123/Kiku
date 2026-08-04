<script lang="ts">
	import { fetchSourceVersions, retryWorkspaceSource } from './api';
	import type { IngestionMetrics, SourceItem, SourceVersion } from './types';
	import { requireAuth } from '$lib/stores/auth';

	interface Props {
		workspaceId: string;
		sources?: SourceItem[];
		metrics?: IngestionMetrics | null;
		onRefresh?: () => void;
	}

	let { workspaceId, sources = [], metrics = null, onRefresh = () => {} }: Props = $props();

	let selectedSourceVersions = $state<{ sourceId: string; versions: SourceVersion[] } | null>(null);
	let loadingVersionId = $state<string | null>(null);
	let retryingSourceId = $state<string | null>(null);
	let actionError = $state<string | null>(null);

	async function handleRetry(sourceId: string) {
		requireAuth(async () => {
			retryingSourceId = sourceId;
			actionError = null;
			try {
				await retryWorkspaceSource(workspaceId, sourceId);
				onRefresh();
			} catch (err: unknown) {
				actionError = err instanceof Error ? err.message : 'Retry failed.';
			} finally {
				retryingSourceId = null;
			}
		});
	}

	async function handleViewVersions(sourceId: string) {
		loadingVersionId = sourceId;
		actionError = null;
		try {
			const versions = await fetchSourceVersions(workspaceId, sourceId);
			selectedSourceVersions = { sourceId, versions };
		} catch (err: unknown) {
			actionError = err instanceof Error ? err.message : 'Failed to fetch version history.';
		} finally {
			loadingVersionId = null;
		}
	}

	function getFileTypeBadge(fileType: string) {
		switch (fileType) {
			case 'markdown':
				return {
					label: 'Markdown',
					bg: 'bg-success-soft text-success-fg border-success-border'
				};
			case 'pdf':
				return {
					label: 'PDF',
					bg: 'bg-destructive-soft text-destructive-fg border-destructive-border'
				};
			default:
				return { label: 'Text', bg: 'bg-accent-soft text-accent border-border' };
		}
	}
</script>

<div class="space-y-6">
	<!-- Telemetry Metrics Card -->
	{#if metrics}
		<div class="grid grid-cols-2 gap-4 sm:grid-cols-4">
			<div class="rounded-xl border border-border bg-surface p-4 shadow-sm">
				<span class="text-xs font-semibold tracking-wider text-muted uppercase">Total Ingested</span
				>
				<p class="mt-1 text-2xl font-bold text-heading">{metrics.total_attempts}</p>
			</div>
			<div class="rounded-xl border border-success-border bg-success-soft p-4 shadow-sm">
				<span class="text-xs font-semibold tracking-wider text-success-fg uppercase"
					>Ready Sources</span
				>
				<p class="mt-1 text-2xl font-bold text-success-fg">{metrics.ready_count}</p>
			</div>
			<div class="rounded-xl border border-destructive-border bg-destructive-soft p-4 shadow-sm">
				<span class="text-xs font-semibold tracking-wider text-destructive-fg uppercase"
					>Failed Jobs</span
				>
				<p class="mt-1 text-2xl font-bold text-destructive-fg">{metrics.failed_count}</p>
			</div>
			<div class="rounded-xl border border-border bg-accent-soft p-4 shadow-sm">
				<span class="text-xs font-semibold tracking-wider text-accent uppercase"
					>Retrying / Queued</span
				>
				<p class="mt-1 text-2xl font-bold text-accent">{metrics.retrying_count}</p>
			</div>
		</div>
	{/if}

	{#if actionError}
		<div
			class="flex items-center justify-between rounded-xl border border-destructive-border bg-destructive-soft p-4 text-sm text-destructive-fg"
		>
			<div class="flex items-center gap-2">
				<svg class="h-5 w-5 text-destructive" fill="none" viewBox="0 0 24 24" stroke="currentColor">
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
					/>
				</svg>
				<span>{actionError}</span>
			</div>
			<button onclick={() => (actionError = null)} class="text-muted hover:text-heading"
				>&times;</button
			>
		</div>
	{/if}

	<!-- Sources List Table / Cards -->
	{#if sources.length === 0}
		<div
			class="rounded-2xl border border-dashed border-border bg-surface p-12 text-center text-muted"
		>
			<svg
				class="mx-auto mb-3 h-12 w-12 text-muted opacity-60"
				fill="none"
				viewBox="0 0 24 24"
				stroke="currentColor"
			>
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="1"
					d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 01-2-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
				/>
			</svg>
			<h4 class="text-base font-semibold text-heading">No Knowledge Sources Added</h4>
			<p class="mt-1 text-sm text-muted">
				Add Markdown, Text, or PDF documents to enable LlamaIndex search retrieval for your
				workspace.
			</p>
		</div>
	{:else}
		<div class="space-y-4">
			{#each sources as source (source.id)}
				{@const typeBadge = getFileTypeBadge(source.file_type)}
				<div
					class="rounded-xl border border-border bg-surface p-5 shadow-sm transition hover:border-border-strong"
				>
					<div class="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
						<div class="flex items-start gap-3">
							<div class="mt-0.5 rounded-lg bg-accent-soft p-2.5 text-accent">
								<svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="1.8"
										d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
									/>
								</svg>
							</div>
							<div>
								<div class="flex flex-wrap items-center gap-2">
									<h4 class="text-base font-bold text-heading">{source.title}</h4>
									<span
										class={`rounded-md border px-2 py-0.5 text-xs font-semibold ${typeBadge.bg}`}
									>
										{typeBadge.label}
									</span>
									<span
										class="rounded-md border border-border bg-surface-raised px-2 py-0.5 font-mono text-xs text-text"
									>
										v{source.current_version}
									</span>
								</div>
								<p class="mt-1 text-xs text-muted">
									ID: <span class="font-mono text-subtle">{source.id}</span> &bull; Updated: {source.updated_at}
								</p>
							</div>
						</div>

						<!-- Status Badge & Actions -->
						<div class="flex items-center gap-3">
							{#if source.status === 'ready'}
								<span
									class="inline-flex items-center gap-1.5 rounded-full border border-success-border bg-success-soft px-3 py-1 text-xs font-semibold text-success-fg"
								>
									<span class="h-2 w-2 rounded-full bg-success"></span>
									Ready
								</span>
							{:else if source.status === 'processing'}
								<span
									class="inline-flex items-center gap-1.5 rounded-full border border-border bg-accent-soft px-3 py-1 text-xs font-semibold text-accent"
								>
									<span class="h-2 w-2 animate-ping rounded-full bg-accent"></span>
									Processing
								</span>
							{:else if source.status === 'queued'}
								<span
									class="inline-flex items-center gap-1.5 rounded-full border border-warning-border bg-warning-soft px-3 py-1 text-xs font-semibold text-warning-fg"
								>
									<span class="h-2 w-2 rounded-full bg-warning"></span>
									Queued
								</span>
							{:else if source.status === 'failed'}
								<span
									class="inline-flex items-center gap-1.5 rounded-full border border-destructive-border bg-destructive-soft px-3 py-1 text-xs font-semibold text-destructive-fg"
								>
									<span class="h-2 w-2 rounded-full bg-destructive"></span>
									Failed
								</span>
							{/if}

							<!-- Action Buttons -->
							<button
								onclick={() => handleViewVersions(source.id)}
								disabled={loadingVersionId === source.id}
								class="rounded-lg border border-border bg-surface-raised px-3 py-1.5 text-xs font-medium text-text transition hover:bg-surface-soft hover:text-heading disabled:opacity-50"
							>
								{loadingVersionId === source.id ? 'Loading...' : 'Versions'}
							</button>

							{#if source.status === 'failed'}
								<button
									onclick={() => handleRetry(source.id)}
									disabled={retryingSourceId === source.id}
									class="inline-flex items-center gap-1 rounded-lg bg-destructive px-3 py-1.5 text-xs font-semibold text-primary-fg transition hover:bg-destructive-hover disabled:opacity-50"
								>
									{#if retryingSourceId === source.id}
										<svg class="h-3.5 w-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
											<circle
												class="opacity-25"
												cx="12"
												cy="12"
												r="10"
												stroke="currentColor"
												stroke-width="4"
											></circle>
											<path
												class="opacity-75"
												fill="currentColor"
												d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
											></path>
										</svg>
										Retrying...
									{:else}
										<svg class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												stroke-width="2"
												d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
											/>
										</svg>
										Retry Job
									{/if}
								</button>
							{/if}
						</div>
					</div>

					{#if source.status === 'failed' && source.status_reason}
						<div
							class="mt-3 rounded-lg border border-destructive-border bg-destructive-soft p-3 text-xs text-destructive-fg"
						>
							<strong class="font-semibold text-destructive-fg">Actionable Failure Reason:</strong>
							{source.status_reason}
						</div>
					{/if}
				</div>
			{/each}
		</div>
	{/if}

	<!-- Version History Modal -->
	{#if selectedSourceVersions}
		<div
			class="animate-fade-in fixed inset-0 z-50 flex items-center justify-center bg-overlay p-4 backdrop-blur-sm"
		>
			<div
				class="w-full max-w-lg rounded-2xl border border-border bg-surface p-6 text-text shadow-2xl"
			>
				<div class="flex items-center justify-between border-b border-border pb-4">
					<h3 class="flex items-center gap-2 text-lg font-bold text-heading">
						Version History: <span class="font-mono text-accent"
							>{selectedSourceVersions.sourceId}</span
						>
					</h3>
					<button
						onclick={() => (selectedSourceVersions = null)}
						class="rounded-lg p-1 text-muted hover:text-heading"
					>
						&times;
					</button>
				</div>

				<div class="mt-4 max-h-80 space-y-3 overflow-y-auto">
					{#each selectedSourceVersions.versions as version (version.version_id)}
						<div
							class="flex items-center justify-between rounded-lg border border-border bg-surface-raised p-3"
						>
							<div>
								<span
									class="rounded bg-accent-soft px-2 py-0.5 font-mono text-xs font-bold text-accent"
									>Version {version.version_number}</span
								>
								<p class="mt-1 max-w-xs truncate font-mono text-xs text-muted">
									{version.file_path}
								</p>
							</div>
							<div class="text-right">
								<span class="text-xs text-text">{(version.file_size / 1024).toFixed(1)} KB</span>
								<p class="text-[10px] text-muted">{version.created_at}</p>
							</div>
						</div>
					{/each}
				</div>

				<div class="mt-6 flex justify-end border-t border-border pt-3">
					<button
						onclick={() => (selectedSourceVersions = null)}
						class="rounded-lg bg-surface-raised px-4 py-2 text-sm font-medium text-heading transition hover:bg-surface-hover"
					>
						Close
					</button>
				</div>
			</div>
		</div>
	{/if}
</div>
