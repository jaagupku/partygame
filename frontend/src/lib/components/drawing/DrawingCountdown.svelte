<script lang="ts">
	import { onMount } from 'svelte';
	import { messages } from '$lib/i18n';
	import { drawingSegment } from './reveal';
	let {
		view,
		current = 0
	}: {
		view: DrawingGameView;
		/** The drawing open on this phone; a nudge appears once the clock has moved past it. */
		current?: number;
	} = $props();
	let now = $state(Date.now() / 1000);
	onMount(() => {
		const id = setInterval(() => (now = Date.now() / 1000), 200);
		return () => clearInterval(id);
	});
	const seconds = $derived(
		Math.max(
			0,
			Math.ceil(view.paused ? (view.remaining_seconds ?? 0) : (view.deadline ?? now) - now)
		)
	);
	const segment = $derived(drawingSegment(view, seconds));
</script>

<p class="text-xl font-bold">
	{view.paused
		? $messages.drawingMashup.paused
		: `${$messages.drawingMashup.timeLeft}: ${seconds}s`}
</p>
{#if segment && !view.paused && segment.index > current}
	<p class="move-on" role="status">{$messages.drawingMashup.moveOn(segment.index + 1)}</p>
{/if}

<style>
	.move-on {
		/* Takes its own line when it sits in a row beside the clock. */
		flex-basis: 100%;
		padding: 0.6rem 0.85rem;
		border: 2px solid var(--party-soft-accent-border);
		border-radius: 0.75rem;
		background: var(--party-soft-accent-bg);
		color: var(--party-soft-accent-text);
		font-weight: 800;
	}
</style>
