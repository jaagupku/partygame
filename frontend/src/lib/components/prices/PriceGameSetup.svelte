<script lang="ts">
	import { onMount, untrack } from 'svelte';
	import { goto } from '$app/navigation';
	import { messages, locale } from '$lib/i18n';
	const {
		initialSettings,
		onsubmit,
		oncancel,
		submitLabel
	}: {
		initialSettings?: GameSetupSettings;
		onsubmit?: (settings: GameSetupSettings) => Promise<void>;
		oncancel?: () => void;
		submitLabel?: string;
	} = $props();
	type Mode = 'guess' | 'compare' | 'mixed';
	type ProductRange = 'groceries' | 'electronics' | 'furniture' | 'antiques' | 'clothing';
	type Availability = {
		ranges: { product_range: ProductRange; available: boolean; captured_at: string | null }[];
		combinations: { mode: Mode; product_ranges: ProductRange[]; questions: number }[];
	};
	let mode = $state<Mode>(untrack(() => initialSettings?.price_settings?.mode ?? 'mixed'));
	let productRanges = $state<ProductRange[]>(
		untrack(() => initialSettings?.price_settings?.product_ranges ?? [])
	);
	let selectionInitialized = untrack(() => Boolean(initialSettings?.price_settings));
	let questions = $state(untrack(() => initialSettings?.price_settings?.questions ?? 10));
	let seconds = $state(untrack(() => initialSettings?.price_settings?.answer_seconds ?? 30));
	let revealSeconds = $state(untrack(() => initialSettings?.price_settings?.reveal_seconds ?? 4));
	let hostEnabled = $state(untrack(() => initialSettings?.host_enabled ?? false));
	let availability = $state<Availability | null>(null);
	let loading = $state(true);
	let failed = $state(false);
	let creating = $state(false);
	let createError = $state<'unavailable' | 'createFailed' | null>(null);
	const playable = $derived(
		availability?.combinations.some(
			(c) =>
				c.mode === mode &&
				c.questions === questions &&
				c.product_ranges.length === productRanges.length &&
				c.product_ranges.every((range) => productRanges.includes(range))
		) ?? false
	);
	async function load() {
		loading = true;
		failed = false;
		try {
			const response = await fetch('/api/v1/game-types/price_guessing/availability');
			if (!response.ok) throw new Error('Availability failed');
			const loaded: Availability = await response.json();
			availability = loaded;
			const available = loaded.ranges
				.filter((range) => range.available)
				.map((range) => range.product_range);
			productRanges = selectionInitialized ? productRanges : available;
			if (available.length) selectionInitialized = true;
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
			if (onsubmit) {
				await onsubmit({
					game_type: 'price_guessing',
					host_enabled: hostEnabled,
					price_settings: {
						mode,
						product_ranges: productRanges,
						questions,
						answer_seconds: seconds,
						reveal_seconds: revealSeconds
					}
				});
				return;
			}
			const response = await fetch('/api/v1/lobby/create', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					game_type: 'price_guessing',
					host_enabled: hostEnabled,
					price_settings: {
						mode,
						product_ranges: productRanges,
						questions,
						answer_seconds: seconds,
						reveal_seconds: revealSeconds
					}
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
			<fieldset class="min-w-0 sm:col-span-2">
				<legend class="label-title">{$messages.priceGame.productRange}</legend>
				<div class="grid gap-2 sm:grid-cols-2">
					{#each availability?.ranges ?? [] as range}
						<label class="flex min-h-12 items-center gap-3 rounded-lg border p-3">
							<input
								type="checkbox"
								value={range.product_range}
								bind:group={productRanges}
								disabled={!range.available}
								aria-describedby={!range.available
									? `unavailable-${range.product_range}`
									: undefined}
							/>
							<span
								>{$messages.priceGame[range.product_range]}
								{#if !range.available}<span
										id={`unavailable-${range.product_range}`}
										class="block text-sm theme-text-muted">{$messages.priceGame.noDataset}</span
									>{/if}
							</span>
						</label>
					{/each}
				</div>
				<p class="mt-2 text-sm theme-text-muted">{$messages.priceGame.categoryMixing}</p>
			</fieldset>
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
			{#if !hostEnabled}
				<label class="input-wrap"
					><span class="label-title">{$messages.priceGame.revealTime}</span><select
						class="input"
						bind:value={revealSeconds}
						>{#each [4, 6, 8, 10, 15] as value}<option {value}
								>{value} {$messages.priceGame.seconds}</option
							>{/each}</select
					></label
				>
			{/if}
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
			>{creating
				? onsubmit
					? $messages.continueGame.preparing
					: $messages.gameCatalog.creating
				: (submitLabel ?? $messages.common.createGame)}</button
		>
	{/if}
	{#if oncancel}<button class="btn btn-ghost" disabled={creating} onclick={oncancel}
			>{$messages.common.back}</button
		>{:else}<a class="btn btn-ghost" href="/">{$messages.common.back}</a>{/if}
</div>
