export interface ChatCitation {
	source_id: string;
	title: string;
	version: number;
	location: string;
	snippet: string;
}

export interface ChatMessage {
	id: string;
	session_id: string;
	role: 'user' | 'assistant';
	content: string;
	citations?: ChatCitation[];
	created_at: string;
}

export interface ChatSession {
	id: string;
	workspace_id: string;
	user_id: string;
	title: string;
	created_at: string;
	updated_at: string;
}
