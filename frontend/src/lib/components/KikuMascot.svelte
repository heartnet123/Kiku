<script lang="ts">
	let { className = '' }: { className?: string } = $props();
</script>

<svg class={className} viewBox="0 0 120 120" aria-hidden="true">
	<ellipse cx="60" cy="24" rx="12" ry="20" fill="#ffb3c0" />
	<ellipse cx="88" cy="38" rx="12" ry="20" transform="rotate(45 88 38)" fill="#ff91a8" />
	<ellipse cx="96" cy="66" rx="12" ry="20" transform="rotate(90 96 66)" fill="#ffb3c0" />
	<ellipse cx="83" cy="92" rx="12" ry="20" transform="rotate(135 83 92)" fill="#ff91a8" />
	<ellipse cx="60" cy="100" rx="12" ry="20" fill="#ffb3c0" />
	<ellipse cx="35" cy="92" rx="12" ry="20" transform="rotate(-135 35 92)" fill="#ff91a8" />
	<ellipse cx="24" cy="66" rx="12" ry="20" transform="rotate(90 24 66)" fill="#ffb3c0" />
	<ellipse cx="35" cy="39" rx="12" ry="20" transform="rotate(-45 35 39)" fill="#ff91a8" />
	<circle cx="60" cy="63" r="31" fill="#fffdfd" stroke="#ff6681" stroke-width="2" />
	<path
		d="M51 81c5 4 13 4 18 0"
		fill="none"
		stroke="#16203d"
		stroke-linecap="round"
		stroke-width="2.5"
	/>
	<circle cx="51" cy="62" r="3" fill="#16203d" />
	<circle cx="69" cy="62" r="3" fill="#16203d" />
	<circle cx="44" cy="71" r="4" fill="#ffc5cd" opacity=".75" />
	<circle cx="76" cy="71" r="4" fill="#ffc5cd" opacity=".75" />
	<path
		d="M38 94c4 7 8 11 11 13M82 94c-4 7-8 11-11 13"
		fill="none"
		stroke="#ff6681"
		stroke-linecap="round"
		stroke-width="3"
	/>
</svg>
