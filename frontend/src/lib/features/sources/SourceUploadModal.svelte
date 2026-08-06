<script lang="ts">
	import { uploadWorkspaceSource } from './api';
	import { getCurrentWorkspaceId } from '$lib/stores/workspace';
	import type { SourceItem } from './types';

	interface Props {
		workspaceId: string;
		isOpen?: boolean;
		onClose?: () => void;
		onUploaded?: (source: SourceItem) => void;
	}

	let { workspaceId, isOpen = false, onClose = () => {}, onUploaded = () => {} }: Props = $props();

	let selectedFile = $state<File | null>(null);
	let isUploading = $state(false);
	let errorMessage = $state<string | null>(null);
	let isDragOver = $state(false);

	function handleFileSelect(event: Event) {
		const target = event.target as HTMLInputElement;
		if (target.files && target.files.length > 0) {
			validateAndSetFile(target.files[0]);
		}
	}

	function handleDrop(event: DragEvent) {
		event.preventDefault();
		isDragOver = false;
		if (event.dataTransfer?.files && event.dataTransfer.files.length > 0) {
			validateAndSetFile(event.dataTransfer.files[0]);
		}
	}

	function validateAndSetFile(file: File) {
		errorMessage = null;
		const name = file.name.toLowerCase();
		if (!name.endsWith('.md') && !name.endsWith('.txt') && !name.endsWith('.pdf')) {
			errorMessage = 'Only Markdown (.md), Text (.txt), and PDF (.pdf) files are supported.';
			selectedFile = null;
			return;
		}
		selectedFile = file;
	}

	async function handleSubmit() {
		if (!selectedFile) return;
		isUploading = true;
		errorMessage = null;

		try {
			const activeId = workspaceId || getCurrentWorkspaceId();
			const source = await uploadWorkspaceSource(selectedFile, activeId);
			onUploaded(source);
			onClose();
			selectedFile = null;
		} catch (err: unknown) {
			errorMessage = err instanceof Error ? err.message : 'Failed to upload source file.';
		} finally {
			isUploading = false;
		}
	}
</script>

{#if isOpen}
	<div
		class="animate-fade-in fixed inset-0 z-50 flex items-center justify-center bg-overlay p-4 backdrop-blur-sm"
	>
		<div
			class="w-full max-w-lg rounded-2xl border border-border bg-surface p-6 text-text shadow-2xl"
		>
			<div class="flex items-center justify-between border-b border-border pb-4">
				<h3 class="flex items-center gap-2 text-xl font-bold tracking-tight text-heading">
					<svg class="h-6 w-6 text-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
						/>
					</svg>
					Add Knowledge Source
				</h3>
				<button
					onclick={onClose}
					class="rounded-lg p-1 text-muted transition hover:bg-surface-raised hover:text-heading"
					aria-label="Close dialog"
				>
					<svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M6 18L18 6M6 6l12 12"
						/>
					</svg>
				</button>
			</div>

			<div class="mt-4 space-y-4">
				<p class="text-sm text-subtle">
					Upload a Markdown (<code class="font-semibold text-accent">.md</code>), plain text (<code
						class="font-semibold text-accent">.txt</code
					>), or PDF (<code class="font-semibold text-accent">.pdf</code>) document. LlamaIndex will
					index its content into your workspace vector store.
				</p>

				<!-- Dropzone -->
				<div
					role="region"
					aria-label="File upload dropzone"
					ondragover={(e) => {
						e.preventDefault();
						isDragOver = true;
					}}
					ondragleave={() => (isDragOver = false)}
					ondrop={handleDrop}
					class={`relative flex flex-col items-center justify-center rounded-xl border-2 border-dashed p-8 text-center transition ${
						isDragOver
							? 'border-accent bg-accent-soft'
							: 'border-border bg-surface-raised hover:border-accent hover:bg-surface-soft'
					}`}
				>
					<input
						type="file"
						accept=".md,.txt,.pdf"
						onchange={handleFileSelect}
						class="absolute inset-0 cursor-pointer opacity-0"
					/>
					<svg
						class="mb-3 h-10 w-10 text-accent"
						fill="none"
						viewBox="0 0 24 24"
						stroke="currentColor"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="1.5"
							d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
						/>
					</svg>
					{#if selectedFile}
						<span class="font-semibold text-accent">{selectedFile.name}</span>
						<span class="mt-1 text-xs text-muted">{(selectedFile.size / 1024).toFixed(1)} KB</span>
					{:else}
						<span class="text-sm font-medium text-heading"
							>Drag and drop your file here, or <span class="text-accent underline">browse</span
							></span
						>
						<span class="mt-1 text-xs text-muted">Supports Markdown, Text, and PDF files</span>
					{/if}
				</div>

				{#if errorMessage}
					<div
						class="flex items-start gap-2 rounded-lg border border-destructive-border bg-destructive-soft p-3 text-xs text-destructive-fg"
					>
						<svg
							class="mt-0.5 h-4 w-4 shrink-0 text-destructive"
							fill="none"
							viewBox="0 0 24 24"
							stroke="currentColor"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
							/>
						</svg>
						<span>{errorMessage}</span>
					</div>
				{/if}
			</div>

			<div class="mt-6 flex justify-end gap-3 border-t border-border pt-4">
				<button
					type="button"
					onclick={onClose}
					disabled={isUploading}
					class="rounded-lg px-4 py-2 text-sm font-medium text-muted transition hover:text-heading disabled:opacity-50"
				>
					Cancel
				</button>
				<button
					type="button"
					onclick={handleSubmit}
					disabled={!selectedFile || isUploading}
					class="flex items-center gap-2 rounded-lg bg-primary px-5 py-2 text-sm font-semibold text-primary-fg shadow-lg transition hover:bg-primary-hover disabled:opacity-50"
				>
					{#if isUploading}
						<svg class="h-4 w-4 animate-spin text-primary-fg" fill="none" viewBox="0 0 24 24">
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
								d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
							></path>
						</svg>
						<span>Ingesting...</span>
					{:else}
						<span>Upload & Ingest</span>
					{/if}
				</button>
			</div>
		</div>
	</div>
{/if}
