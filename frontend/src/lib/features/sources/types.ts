export type SourceStatus = 'queued' | 'processing' | 'ready' | 'failed';

export type FileType = 'markdown' | 'text' | 'pdf';

export type SourceItem = {
	id: string;
	workspace_id: string;
	title: string;
	file_type: FileType;
	current_version: number;
	status: SourceStatus;
	status_reason?: string | null;
	page: number;
	updated_at: string;
};

export type SourceVersion = {
	version_id: string;
	source_id: string;
	version_number: number;
	file_path: string;
	file_size: number;
	created_at: string;
};

export type IngestionMetrics = {
	total_attempts: number;
	ready_count: number;
	failed_count: number;
	retrying_count: number;
	by_type: Record<string, Record<string, number>>;
};
