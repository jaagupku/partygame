<script lang="ts">
	import { onMount } from 'svelte';
	import DrawingDisplay from '$lib/components/DrawingDisplay.svelte';
	import { messages } from '$lib/i18n';
	import { drawingText } from './helpers';
	let {
		items,
		lobbyId,
		runId,
		language
	}: { items: MashupArtwork[]; lobbyId: string; runId: string; language: 'en' | 'et' } = $props();
	let index = $state(0);
	let paused = $state(false);
	let value = $state<DrawingSubmission | null>(null);
	let failed = $state(false);
	let retry = $state(0);
	let nextAt = Date.now() + 7000;
	const cache = new Map<string, DrawingSubmission>();
	const item = $derived(items[index % items.length]);
	async function load(id: string, signal: AbortSignal) {
		if (cache.has(id)) return cache.get(id)!;
		const response = await fetch(`/api/v1/lobby/${lobbyId}/drawing/${runId}/${id}`, { signal });
		if (!response.ok) throw new Error('Gallery unavailable');
		const drawing: DrawingSubmission = await response.json();
		if (signal.aborted) return null;
		cache.set(id, drawing);
		return drawing;
	}
	$effect(() => {
		const current = item;
		const following = items[(index + 1) % items.length];
		void retry;
		const controller = new AbortController();
		value = current ? (cache.get(current.id) ?? null) : null;
		failed = false;
		if (current) {
			void load(current.id, controller.signal)
				.then((drawing) => {
					if (!controller.signal.aborted) value = drawing;
					if (following) return load(following.id, controller.signal);
				})
				.catch(() => {
					if (!controller.signal.aborted && !value) failed = true;
				});
			for (const key of cache.keys())
				if (key !== current.id && key !== following?.id) cache.delete(key);
		}
		return () => controller.abort();
	});
	function move(amount: number) {
		index = (index + amount + items.length) % items.length;
		nextAt = Date.now() + 7000;
	}
	onMount(() => {
		paused = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;
		const timer = setInterval(() => {
			if (failed) retry += 1;
			if (!paused && Date.now() >= nextAt) move(1);
		}, 1000);
		return () => clearInterval(timer);
	});
</script>

<aside class="card stack-md gallery-card" aria-label={$messages.drawingMashup.gallery}>
	<h2 class="text-xl font-bold">{$messages.drawingMashup.gallery} · {index + 1}/{items.length}</h2>
	{#if item}
		<h3 class="text-xl font-bold">{drawingText(item.topic, 'topic', language)}</h3>
		<p>{$messages.drawingMashup.criterion}: {drawingText(item.criterion, 'criterion', language)}</p>
		{#if value}<div class="gallery-image"><DrawingDisplay drawing={value} animate /></div>{:else}<p
				role="status"
			>
				{failed ? $messages.drawingMashup.galleryError : $messages.common.loading}
			</p>{/if}
		<p>
			<strong>{item.player_name}</strong> · {item.points}
			{$messages.drawingMashup.points} · {$messages.drawingMashup.voteCount(item.vote_count)}
		</p>
	{/if}
	<div class="flex flex-wrap gap-2">
		<button class="btn btn-ghost" onclick={() => move(-1)}
			>{$messages.drawingMashup.previous}</button
		>
		<button
			class="btn btn-ghost"
			onclick={() => {
				paused = !paused;
				nextAt = Date.now() + 7000;
			}}>{paused ? $messages.drawingMashup.resume : $messages.drawingMashup.pause}</button
		>
		<button class="btn btn-ghost" onclick={() => move(1)}>{$messages.drawingMashup.next}</button>
	</div>
</aside>

<style>
	.gallery-card {
		min-width: 0;
		min-height: 0;
		overflow: auto;
	}
	.gallery-image {
		flex-shrink: 0;
		width: 100%;
		aspect-ratio: 4 / 3;
		max-height: 55dvh;
		min-height: 0;
	}
	.gallery-image :global(canvas) {
		width: 100%;
		height: 100%;
		object-fit: contain;
	}
	@media (max-width: 760px) {
		.gallery-card {
			height: max-content;
			overflow: visible;
		}
	}
</style>
