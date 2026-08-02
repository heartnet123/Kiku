import { writable } from 'svelte/store';
import type { ChatSession } from './types';

/** Shared store so Sidebar and ChatThread can synchronise the active session
 *  without prop-drilling through AppShell. */
export const activeSessionStore = writable<ChatSession | null>(null);
