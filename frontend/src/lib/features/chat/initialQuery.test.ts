import { describe, expect, it } from 'vitest';
import { consumeInitialQuery, storeInitialQuery } from './initialQuery';

describe('initial chat query handoff', () => {
	it('stores a query for a session and consumes it only once', () => {
		const values = new Map<string, string>();
		const storage = {
			getItem: (key: string) => values.get(key) ?? null,
			setItem: (key: string, value: string) => values.set(key, value),
			removeItem: (key: string) => values.delete(key)
		};

		storeInitialQuery('session/1', '  What is Kiku?  ', storage);

		expect(consumeInitialQuery('session/1', storage)).toBe('What is Kiku?');
		expect(consumeInitialQuery('session/1', storage)).toBeNull();
	});
});
