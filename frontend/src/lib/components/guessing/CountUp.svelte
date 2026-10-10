<script lang="ts">
	import { onMount, untrack } from 'svelte';
	import { COUNT_UP_DELAY_MS, COUNT_UP_MS, countUpValue } from './guess-reveal';

	let {
		value,
		format,
		animate = false
	}: { value: number; format: (value: number) => string; animate?: boolean } = $props();

	// Only a live reveal counts; reconnects, history and reduced motion show the result.
	const playing = untrack(
		() =>
			animate &&
			!(
				typeof window !== 'undefined' &&
				window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
			)
	);
	let elapsed = $state(playing ? 0 : Infinity);
	const shown = $derived(countUpValue(value, elapsed));

	onMount(() => {
		if (!playing) return;
		const start = performance.now();
		let frame = requestAnimationFrame(function tick(now) {
			elapsed = now - start;
			if (elapsed < COUNT_UP_DELAY_MS + COUNT_UP_MS) frame = requestAnimationFrame(tick);
		});
		return () => cancelAnimationFrame(frame);
	});
</script>

{#if elapsed < COUNT_UP_DELAY_MS + COUNT_UP_MS}
	<!-- Screen readers get the final value once, not every intermediate frame. -->
	<span aria-hidden="true">{format(shown)}</span><span class="sr-only">{format(value)}</span>
{:else}{format(value)}{/if}
