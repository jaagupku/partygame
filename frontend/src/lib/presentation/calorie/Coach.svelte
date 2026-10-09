<script lang="ts">
	let {
		pose,
		message = '',
		compact = false
	}: {
		/** The welcoming pose is part of studio.svg. */
		pose: 'thinking' | 'reveal' | 'celebrate';
		message?: string;
		compact?: boolean;
	} = $props();
</script>

<div class="studio-coach" class:studio-coach-compact={compact} data-coach-pose={pose}>
	{#key pose}<img
			src={`/presentation/calorie/coach-${pose}.svg`}
			alt=""
			width="240"
			height="260"
		/>{/key}
	{#if message}<p>{message}</p>{/if}
</div>
