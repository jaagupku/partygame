<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { messages, locale } from '$lib/i18n';
	type Mode = 'guess' | 'compare' | 'mixed';
	type ProductRange = 'groceries' | 'electronics' | 'both';
	type Availability = {
		ranges: { product_range: ProductRange; available: boolean; captured_at: string | null }[];
		combinations: { mode: Mode; product_range: ProductRange; questions: number }[];
	};
	let mode = $state<Mode>('mixed');
	let productRange = $state<ProductRange>('both');
	let questions = $state(10);
	let seconds = $state(30);
	let hostEnabled = $state(false);
	let availability = $state<Availability | null>(null);
	let loading = $state(true);
	let failed = $state(false);
	let creating = $state(false);
	let createError = $state<'unavailable' | 'createFailed' | null>(null);
	const playable = $derived(
		availability?.combinations.some(
			(c) => c.mode === mode && c.product_range === productRange && c.questions === questions
		) ?? false
	);
	async function load() {
		loading = true;
		failed = false;
		try {
			const response = await fetch('/api/v1/game-types/price_guessing/availability');
			if (!response.ok) throw new Error('Availability failed');
			availability = await response.json();
		} catch {
			failed = true;
		} finally {
			loading = false;
		}
	}
	onMount(() => {
		void load();
	});
	async function create() {
		if (!playable || creating) return;
		creating = true;
		createError = null;
		try {
			const response = await fetch('/api/v1/lobby/create', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					game_type: 'price_guessing',
					host_enabled: hostEnabled,
					price_settings: { mode, product_range: productRange, questions, answer_seconds: seconds }
				})
			});
			if (!response.ok) {
				createError = response.status === 409 ? 'unavailable' : 'createFailed';
				return;
			}
			const lobby: Lobby = await response.json();
			await goto(`/host/${lobby.join_code}`);
		} catch {
			createError = 'createFailed';
		} finally {
			creating = false;
		}
	}
</script>

<h1 class="page-title">{$messages.priceGame.title}</h1>
<p class="page-subtitle">{$messages.priceGame.subtitle}</p>
<div class="stack-lg">
	<p>{$messages.priceGame.rules}</p>
	<p class="theme-text-muted">{$messages.priceGame.priceBasis}</p>
	{#if loading}<p role="status">{$messages.priceGame.loading}</p>
	{:else if failed}<div role="alert">
			<p>{$messages.priceGame.loadFailed}</p>
			<button class="btn btn-primary" onclick={load}>{$messages.priceGame.retry}</button>
		</div>
	{:else}
		<fieldset disabled={creating} class="card grid min-w-0 gap-4 sm:grid-cols-2">
			<label class="input-wrap"
				><span class="label-title">{$messages.priceGame.mode}</span><select
					class="input"
					bind:value={mode}
					>{#each ['guess', 'compare', 'mixed'] as option}<option value={option}
							>{$messages.priceGame[option as Mode]}</option
						>{/each}</select
				></label
			>
			<label class="input-wrap"
				><span class="label-title">{$messages.priceGame.productRange}</span><select
					class="input"
					bind:value={productRange}
					>{#each ['groceries', 'electronics', 'both'] as option}<option value={option}
							>{$messages.priceGame[option as ProductRange]}</option
						>{/each}</select
				></label
			>
			<label class="input-wrap"
				><span class="label-title">{$messages.priceGame.questions}</span><select
					class="input"
					bind:value={questions}
					>{#each [5, 10, 15, 20] as value}<option {value}>{value}</option>{/each}</select
				></label
			>
			<label class="input-wrap"
				><span class="label-title">{$messages.priceGame.answerTime}</span><select
					class="input"
					bind:value={seconds}
					>{#each [15, 30, 45, 60] as value}<option {value}
							>{value} {$messages.priceGame.seconds}</option
						>{/each}</select
				></label
			>
			<label class="input-wrap"
				><span class="label-title">{$messages.priceGame.progression}</span><select
					class="input"
					bind:value={hostEnabled}
					><option value={false}>{$messages.priceGame.automatic}</option><option value={true}
						>{$messages.priceGame.hostPaced}</option
					></select
				></label
			>
		</fieldset>
		{#each availability?.ranges ?? [] as range}<p class="theme-text-muted text-sm">
				{$messages.priceGame[range.product_range]}: {range.captured_at
					? `${$messages.priceGame.captured} ${new Date(range.captured_at).toLocaleDateString($locale)}`
					: $messages.priceGame.noDataset}
			</p>{/each}
		{#if !playable}<p role="status">{$messages.priceGame.unavailable}</p>
			<button class="btn btn-ghost" onclick={load}>{$messages.priceGame.retry}</button>{/if}
		{#if createError}<p role="alert">{$messages.priceGame[createError]}</p>{/if}
		<button class="btn btn-primary min-h-16" disabled={!playable || creating} onclick={create}
			>{creating ? $messages.gameCatalog.creating : $messages.common.createGame}</button
		>
	{/if}
	<a class="btn btn-ghost" href="/">{$messages.common.back}</a>
</div>
