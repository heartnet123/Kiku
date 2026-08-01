<script lang="ts">
	import { fetchSourceVersions, retryWorkspaceSource } from './api';
	import type { IngestionMetrics, SourceItem, SourceVersion } from './types';

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
					bg: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
				};
			case 'pdf':
				return { label: 'PDF', bg: 'bg-rose-500/10 text-rose-400 border-rose-500/20' };
			default:
				return { label: 'Text', bg: 'bg-sky-500/10 text-sky-400 border-sky-500/20' };
		}
	}
</script>

<div class="space-y-6">
	<!-- Telemetry Metrics Card -->
	{#if metrics}
		<div class="grid grid-cols-2 gap-4 sm:grid-cols-4">
			<div class="rounded-xl border border-white/10 bg-slate-900/60 p-4 backdrop-blur-sm">
				<span class="text-xs font-semibold tracking-wider text-slate-400 uppercase"
					>Total Ingested</span
				>
				<p class="mt-1 text-2xl font-bold text-white">{metrics.total_attempts}</p>
			</div>
			<div class="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4 backdrop-blur-sm">
				<span class="text-xs font-semibold tracking-wider text-emerald-400 uppercase"
					>Ready Sources</span
				>
				<p class="mt-1 text-2xl font-bold text-emerald-400">{metrics.ready_count}</p>
			</div>
			<div class="rounded-xl border border-red-500/20 bg-red-500/5 p-4 backdrop-blur-sm">
				<span class="text-xs font-semibold tracking-wider text-red-400 uppercase">Failed Jobs</span>
				<p class="mt-1 text-2xl font-bold text-red-400">{metrics.failed_count}</p>
			</div>
			<div class="rounded-xl border border-indigo-500/20 bg-indigo-500/5 p-4 backdrop-blur-sm">
				<span class="text-xs font-semibold tracking-wider text-indigo-400 uppercase"
					>Retrying / Queued</span
				>
				<p class="mt-1 text-2xl font-bold text-indigo-400">{metrics.retrying_count}</p>
			</div>
		</div>
	{/if}

	{#if actionError}
		<div
			class="flex items-center justify-between rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300"
		>
			<div class="flex items-center gap-2">
				<svg class="h-5 w-5 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
					/>
				</svg>
				<span>{actionError}</span>
			</div>
			<button onclick={() => (actionError = null)} class="text-slate-400 hover:text-white"
				>&times;</button
			>
		</div>
	{/if}

	<!-- Sources List Table / Cards -->
	{#if sources.length === 0}
		<div
			class="rounded-2xl border border-dashed border-white/10 bg-slate-900/40 p-12 text-center text-slate-400"
		>
			<svg
				class="mx-auto mb-3 h-12 w-12 text-slate-600"
				fill="none"
				viewBox="0 0 24 24"
				stroke="currentColor"
			>
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="1"
					d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
				/>
			</svg>
			<h4 class="text-base font-semibold text-slate-200">No Knowledge Sources Added</h4>
			<p class="mt-1 text-sm text-slate-500">
				Add Markdown, Text, or PDF documents to enable LlamaIndex search retrieval for your
				workspace.
			</p>
		</div>
	{:else}
		<div class="space-y-4">
			{#each sources as source (source.id)}
				{@const typeBadge = getFileTypeBadge(source.file_type)}
				<div
					class="rounded-xl border border-white/10 bg-slate-900/80 p-5 shadow-lg transition hover:border-white/20"
				>
					<div class="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
						<div class="flex items-start gap-3">
							<div class="mt-0.5 rounded-lg bg-indigo-500/10 p-2.5 text-indigo-400">
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
									<h4 class="text-base font-bold text-white">{source.title}</h4>
									<span
										class={`rounded-md border px-2 py-0.5 text-xs font-semibold ${typeBadge.bg}`}
									>
										{typeBadge.label}
									</span>
									<span
										class="rounded-md border border-white/10 bg-white/5 px-2 py-0.5 font-mono text-xs text-slate-300"
									>
										v{source.current_version}
									</span>
								</div>
								<p class="mt-1 text-xs text-slate-400">
									ID: <span class="font-mono text-slate-500">{source.id}</span> &bull; Updated: {source.updated_at}
								</p>
							</div>
						</div>

						<!-- Status Badge & Actions -->
						<div class="flex items-center gap-3">
							{#if source.status === 'ready'}
								<span
									class="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-xs font-semibold text-emerald-400"
								>
									<span class="h-2 w-2 rounded-full bg-emerald-400"></span>
									Ready
								</span>
							{:else if source.status === 'processing'}
								<span
									class="inline-flex items-center gap-1.5 rounded-full border border-blue-500/30 bg-blue-500/10 px-3 py-1 text-xs font-semibold text-blue-400"
								>
									<span class="h-2 w-2 animate-ping rounded-full bg-blue-400"></span>
									Processing
								</span>
							{:else if source.status === 'queued'}
								<span
									class="inline-flex items-center gap-1.5 rounded-full border border-amber-500/30 bg-amber-500/10 px-3 py-1 text-xs font-semibold text-amber-400"
								>
									<span class="h-2 w-2 rounded-full bg-amber-400"></span>
									Queued
								</span>
							{:else if source.status === 'failed'}
								<span
									class="inline-flex items-center gap-1.5 rounded-full border border-red-500/30 bg-red-500/10 px-3 py-1 text-xs font-semibold text-red-400"
								>
									<span class="h-2 w-2 rounded-full bg-red-400"></span>
									Failed
								</span>
							{/if}

							<!-- Action Buttons -->
							<button
								onclick={() => handleViewVersions(source.id)}
								disabled={loadingVersionId === source.id}
								class="rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-xs font-medium text-slate-300 transition hover:bg-white/10 hover:text-white disabled:opacity-50"
							>
								{loadingVersionId === source.id ? 'Loading...' : 'Versions'}
							</button>

							{#if source.status === 'failed'}
								<button
									onclick={() => handleRetry(source.id)}
									disabled={retryingSourceId === source.id}
									class="inline-flex items-center gap-1 rounded-lg bg-red-600/80 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-red-500 disabled:opacity-50"
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
							class="mt-3 rounded-lg border border-red-500/20 bg-red-500/10 p-3 text-xs text-red-300"
						>
							<strong class="font-semibold text-red-200">Actionable Failure Reason:</strong>
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
			class="animate-fade-in fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm"
		>
			<div
				class="w-full max-w-lg rounded-2xl border border-white/10 bg-slate-900 p-6 text-slate-100 shadow-2xl"
			>
				<div class="flex items-center justify-between border-b border-white/10 pb-4">
					<h3 class="flex items-center gap-2 text-lg font-bold text-white">
						Version History: <span class="font-mono text-indigo-400"
							>{selectedSourceVersions.sourceId}</span
						>
					</h3>
					<button
						onclick={() => (selectedSourceVersions = null)}
						class="rounded-lg p-1 text-slate-400 hover:text-white"
					>
						&times;
					</button>
				</div>

				<div class="mt-4 max-h-80 space-y-3 overflow-y-auto">
					{#each selectedSourceVersions.versions as version (version.version_id)}
						<div
							class="flex items-center justify-between rounded-lg border border-white/10 bg-slate-800/60 p-3"
						>
							<div>
								<span
									class="rounded bg-indigo-500/20 px-2 py-0.5 font-mono text-xs font-bold text-indigo-300"
									>Version {version.version_number}</span
								>
								<p class="mt-1 max-w-xs truncate font-mono text-xs text-slate-400">
									{version.file_path}
								</p>
							</div>
							<div class="text-right">
								<span class="text-xs text-slate-300"
									>{(version.file_size / 1024).toFixed(1)} KB</span
								>
								<p class="text-[10px] text-slate-500">{version.created_at}</p>
							</div>
						</div>
					{/each}
				</div>

				<div class="mt-6 flex justify-end border-t border-white/10 pt-3">
					<button
						onclick={() => (selectedSourceVersions = null)}
						class="rounded-lg bg-white/10 px-4 py-2 text-sm font-medium text-white transition hover:bg-white/20"
					>
						Close
					</button>
				</div>
			</div>
		</div>
	{/if}
</div>
