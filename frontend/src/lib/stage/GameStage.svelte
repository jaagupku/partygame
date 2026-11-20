<script lang="ts">
	import { onMount, type Snippet } from 'svelte';
	import { STAGE_HEIGHT, STAGE_WIDTH, stageScale } from './stage';

	let { children }: { children: Snippet } = $props();
	let width = $state(0);
	let height = $state(0);
	const scale = $derived(stageScale(width, height));

	// `rem` follows the browser's font-size preference; pin it so every display lays out alike.
	onMount(() => {
		const root = document.documentElement;
		const previous = root.style.fontSize;
		root.style.fontSize = '16px';
		return () => {
			root.style.fontSize = previous;
		};
	});
</script>

<!-- A fixed design-size box scaled as one unit: every display shows the same picture. -->
<div class="game-stage-viewport" bind:clientWidth={width} bind:clientHeight={height}>
	<div
		class="game-stage"
		style:width={`${STAGE_WIDTH}px`}
		style:height={`${STAGE_HEIGHT}px`}
		style:--stage-vw={`${STAGE_WIDTH / 100}px`}
		style:--stage-vh={`${STAGE_HEIGHT / 100}px`}
		style:transform={`translate(-50%, -50%) scale(${scale})`}
		style:visibility={scale ? undefined : 'hidden'}
	>
		{@render children()}
	</div>
</div>

<style>
	.game-stage-viewport {
		position: relative;
		width: 100%;
		height: 100%;
		overflow: hidden;
	}
	/* The transform also makes the stage the containing block for fixed descendants. */
	.game-stage {
		position: absolute;
		top: 50%;
		left: 50%;
		overflow: hidden;
		transform-origin: center;
	}
</style>
