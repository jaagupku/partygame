<script lang="ts">
	import { onMount } from 'svelte';
	import DrawingDisplay from '$lib/components/DrawingDisplay.svelte';
	import { messages } from '$lib/i18n';
	import { drawingText } from './helpers';
	import DrawingResults from './DrawingResults.svelte';
	let { view }: { view: DrawingGameView } = $props();
	let now = $state(Date.now() / 1000);
	onMount(() => {
		const timer = setInterval(() => (now = Date.now() / 1000), 200);
		return () => clearInterval(timer);
	});
	const seconds = $derived(
		Math.max(
			0,
			Math.ceil(view.paused ? (view.remaining_seconds ?? 0) : (view.deadline ?? now) - now)
		)
	);
	const phaseTitle = $derived(
		$messages.drawingMashup[view.phase as 'writing' | 'drawing' | 'voting' | 'results'] ?? ''
	);
</script>

<section class="stack-md drawing-stage">
	<header class="flex flex-wrap items-center justify-between gap-4">
		<h2 class="text-2xl font-bold">{phaseTitle}</h2>
		{#if view.phase !== 'results'}<p class="text-xl font-bold">
				{view.paused
					? $messages.drawingMashup.paused
					: `${$messages.drawingMashup.timeLeft}: ${seconds}s`}
			</p>{/if}
	</header>
	{#if view.matchup}
		<p class="theme-text-muted">{view.matchup_number} / {view.matchup_count}</p>
		<h3 class="text-3xl font-black">{drawingText(view.matchup.topic, 'topic', view.language)}</h3>
		<p class="text-xl">
			<strong>{$messages.drawingMashup.criterion}:</strong>
			{drawingText(view.matchup.criterion, 'criterion', view.language)}
		</p>
		{#if view.phase === 'results'}
			{#key `${view.matchup.id}:${view.phase_id}`}<DrawingResults {view} />{/key}
		{:else}
			<div class="grid gap-4 md:grid-cols-3">
				{#each view.matchup.drawings as artwork, i (artwork.id)}
					<article class="card stack-sm">
						<p class="font-bold">{String.fromCharCode(65 + i)}</p>
						<DrawingDisplay drawing={artwork.value} />
					</article>
				{/each}
			</div>
		{/if}
	{:else}
		<p class="text-xl">{$messages.drawingMashup.waiting}</p>
		{#if view.phase === 'drawing'}<p>{$messages.drawingMashup.criterionHidden}</p>{/if}
	{/if}
	{#if view.phase !== 'results'}<p class="theme-text-muted">
			{$messages.drawingMashup.progress}: {view.ready_ids.length} / {view.participant_ids.length}
		</p>{/if}
</section>

<style>
	.drawing-stage {
		padding: 1rem;
		overflow: auto;
		max-height: 100%;
	}
</style>
