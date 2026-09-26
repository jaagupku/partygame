<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { onMount } from 'svelte';
	import { encodeDefinitionIdForPath } from '$lib/definition-paths.js';
	import { loadGameCatalog, type GameType } from '$lib/game-catalog';
	import { messages } from '$lib/i18n';
	import PriceGameSetup from '$lib/components/prices/PriceGameSetup.svelte';

	let definitions = $state<DefinitionSummary[]>([]);
	let definitionId = $state('');
	let hostEnabled = $state(true);
	let selectedDefinition = $state<GameDefinition | null>(null);
	let loadingDefinition = $state(false);
	let catalog = $state<GameType[]>([]);
	let loading = $state(true);
	let setupFailed = $state(false);
	let previewFailed = $state(false);
	let createFailed = $state(false);
	let creating = $state(false);
	let previewRequest = 0;
	const gameType = $derived(page.url.searchParams.get('game') ?? 'trivia');
	const selectedGame = $derived(catalog.find((game) => game.id === gameType));
	const available = $derived(selectedGame?.availability === 'available');
	const selectedDefinitionSummary = $derived(
		definitions.find((definition) => definition.id === definitionId) ?? null
	);

	async function loadSetup() {
		loading = true;
		setupFailed = false;
		try {
			const [games, response] = await Promise.all([
				loadGameCatalog(),
				fetch('/api/v1/definitions')
			]);
			if (!response.ok) throw new Error('Setup failed');
			catalog = games;
			definitions = await response.json();
			definitionId =
				definitions.find((definition) => definition.id === 'quiz_demo')?.id ??
				definitions[0]?.id ??
				'';
		} catch {
			setupFailed = true;
		} finally {
			loading = false;
		}
	}

	onMount(() => {
		if (gameType !== 'price_guessing') void loadSetup();
	});

	$effect(() => {
		if (definitionId) void loadDefinition(definitionId);
	});

	async function loadDefinition(id: string) {
		const request = ++previewRequest;
		loadingDefinition = true;
		previewFailed = false;
		selectedDefinition = null;
		createFailed = false;
		try {
			const response = await fetch(`/api/v1/definitions/${encodeDefinitionIdForPath(id)}`);
			if (!response.ok) throw new Error('Preview failed');
			const definition: GameDefinition = await response.json();
			if (request === previewRequest) selectedDefinition = definition;
		} catch {
			if (request === previewRequest) previewFailed = true;
		} finally {
			if (request === previewRequest) loadingDefinition = false;
		}
	}

	async function createGame() {
		if (creating || !available || !selectedDefinition || loadingDefinition) return;
		creating = true;
		createFailed = false;
		try {
			const response = await fetch('/api/v1/lobby/create', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					game_type: gameType,
					definition_id: definitionId,
					host_enabled: hostEnabled
				})
			});
			if (!response.ok) throw new Error('Creation failed');
			const lobby: Lobby = await response.json();
			await goto(`/host/${lobby.join_code}`);
		} catch {
			createFailed = true;
		} finally {
			creating = false;
		}
	}
</script>

<svelte:head>
	<title>{$messages.create.title} | {$messages.common.appName}</title>
</svelte:head>

{#if gameType === 'price_guessing'}
	<PriceGameSetup />
{:else}
	<div class="flex flex-wrap items-start justify-between gap-4">
		<div>
			<h1 class="page-title text-left">{$messages.create.title}</h1>
			<p class="page-subtitle text-left">{$messages.create.subtitle}</p>
		</div>
	</div>

	{#if loading}
		<p role="status">{$messages.gameCatalog.loading}</p>
	{:else if setupFailed}
		<div class="card stack-md" role="alert">
			<p>{$messages.gameCatalog.setupFailed}</p>
			<button class="btn btn-primary" onclick={loadSetup}>{$messages.gameCatalog.retry}</button>
		</div>
	{:else if !available}
		<div class="card stack-md">
			<p role="status">{$messages.gameCatalog.unavailable}</p>
			<a class="btn btn-ghost" href="/">{$messages.common.back}</a>
		</div>
	{:else}
		<div class="stack-lg">
			<section class="card stack-md">
				<label class="input-wrap">
					<span class="label-title">{$messages.create.gameDefinition}</span>
					<div class="select-shell">
						<select
							bind:value={definitionId}
							disabled={creating}
							class="input select-input text-lg"
						>
							{#each definitions as definition}
								<option value={definition.id}>{definition.title}</option>
							{/each}
						</select>
						<span class="select-chevron" aria-hidden="true">▾</span>
					</div>
					{#if selectedDefinitionSummary}
						<p class="theme-text-muted text-sm font-semibold">
							{$messages.common.selected}: {selectedDefinitionSummary.title}
						</p>
					{/if}
				</label>

				<label
					class="theme-surface-muted flex items-center justify-between gap-4 rounded-2xl border px-4 py-3"
				>
					<div>
						<p class="theme-text label-title text-xl">{$messages.create.hostEnabledMode}</p>
						<p class="theme-text-muted text-sm">{$messages.create.hostEnabledHelp}</p>
					</div>
					<input bind:checked={hostEnabled} disabled={creating} type="checkbox" class="h-6 w-6" />
				</label>
			</section>

			<section class="card stack-md">
				<div class="flex items-start justify-between gap-4">
					<div>
						<h2 class="label-title text-2xl">{$messages.create.definitionPreview}</h2>
						{#if loadingDefinition}
							<p class="theme-text-muted">{$messages.create.loadingDefinitionDetails}</p>
						{:else if previewFailed}
							<p role="alert">{$messages.gameCatalog.previewFailed}</p>
							<button class="btn btn-ghost" onclick={() => loadDefinition(definitionId)}
								>{$messages.gameCatalog.retry}</button
							>
						{:else if selectedDefinition}
							<p class="theme-text-muted">
								{selectedDefinition.description ?? $messages.create.noDescriptionProvided}
							</p>
						{:else}
							<p class="theme-text-muted">{$messages.create.noDefinitionSelected}</p>
						{/if}
					</div>
					{#if selectedDefinition}
						<div class="theme-soft-primary rounded-2xl border px-4 py-3 text-right">
							<p class="text-sm uppercase tracking-wide">{$messages.common.rounds}</p>
							<p class="text-3xl font-extrabold">{selectedDefinition.rounds.length}</p>
						</div>
					{/if}
				</div>

				{#if selectedDefinition}
					<div class="grid gap-3 md:grid-cols-2">
						{#each selectedDefinition.rounds as round}
							<div class="theme-surface-muted rounded-2xl border p-4">
								<h3 class="theme-text text-xl font-bold">{round.title ?? round.id}</h3>
								<p class="theme-text-muted mt-1 text-sm">
									{round.steps.length}
									{$messages.common.steps}
								</p>
								<ul class="mt-3 space-y-2">
									{#each round.steps.slice(0, 3) as step}
										<li class="theme-surface rounded-xl border px-3 py-2">
											<div class="theme-text font-semibold">{step.title}</div>
											<div class="theme-text-muted text-sm">
												{step.player_input.kind} · {step.evaluation.type_} ·
												{step.timer.seconds ?? 0}s
											</div>
										</li>
									{/each}
								</ul>
							</div>
						{/each}
					</div>
				{/if}
			</section>

			{#if definitions.length === 0}<p role="status">{$messages.gameCatalog.empty}</p>{/if}
			{#if createFailed}<p role="alert">{$messages.gameCatalog.createFailed}</p>{/if}
			<div class="flex flex-wrap gap-4">
				<button class="btn btn-ghost min-h-16 flex-1 text-2xl" onclick={() => goto('/')}>
					{$messages.common.back}
				</button>
				<button
					class="btn btn-primary min-h-16 flex-[2] text-3xl"
					onclick={createGame}
					disabled={creating || loadingDefinition || !selectedDefinition}
					>{creating ? $messages.gameCatalog.creating : $messages.common.createGame}</button
				>
			</div>
		</div>
	{/if}
{/if}
