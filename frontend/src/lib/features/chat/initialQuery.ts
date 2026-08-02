export interface QueryStorage {
	getItem(key: string): string | null;
	setItem(key: string, value: string): void;
	removeItem(key: string): void;
}

const STORAGE_PREFIX = 'kiku_chat_initial_query:';

function getStorage(storage?: QueryStorage): QueryStorage | null {
	if (storage) return storage;
	if (typeof window === 'undefined') return null;
	return window.sessionStorage;
}

function storageKey(sessionId: string): string {
	return STORAGE_PREFIX + sessionId;
}

export function storeInitialQuery(sessionId: string, query: string, storage?: QueryStorage): void {
	const normalizedQuery = query.trim();
	const targetStorage = getStorage(storage);
	if (!targetStorage || !normalizedQuery) return;
	targetStorage.setItem(storageKey(sessionId), normalizedQuery);
}

export function consumeInitialQuery(sessionId: string, storage?: QueryStorage): string | null {
	const targetStorage = getStorage(storage);
	if (!targetStorage) return null;
	const key = storageKey(sessionId);
	const query = targetStorage.getItem(key);
	targetStorage.removeItem(key);
	return query?.trim() || null;
}
