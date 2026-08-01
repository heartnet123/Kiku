<script lang="ts">
	export type IconName =
		| 'chart'
		| 'chevron-down'
		| 'chevron-right'
		| 'document'
		| 'external'
		| 'help'
		| 'home'
		| 'search'
		| 'settings'
		| 'sparkle'
		| 'users';

	const icons: Record<IconName, string> = {
		chart: 'solar:chart-2-linear',
		'chevron-down': 'solar:alt-arrow-down-linear',
		'chevron-right': 'solar:alt-arrow-right-linear',
		document: 'solar:document-text-linear',
		external: 'solar:square-arrow-up-linear',
		help: 'solar:question-circle-linear',
		home: 'solar:home-2-linear',
		search: 'solar:magnifer-linear',
		settings: 'solar:settings-linear',
		sparkle: 'solar:stars-minimalistic-linear',
		users: 'solar:users-group-rounded-linear'
	};

	let {
		name,
		size = 20,
		className = ''
	}: { name: IconName; size?: number; className?: string } = $props();
</script>

<iconify-icon icon={icons[name]} class={className} width={size} height={size} aria-hidden="true"
></iconify-icon>
