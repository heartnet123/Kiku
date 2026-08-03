import type { LayoutServerLoad } from './$types';

export const load: LayoutServerLoad = ({ locals }) => {
	return {
		authState: locals.authState ?? null,
		workspaces: locals.workspaces ?? []
	};
};
