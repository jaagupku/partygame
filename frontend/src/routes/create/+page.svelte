<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { messages } from '$lib/i18n';

	let definitions = $state<DefinitionSummary[]>([]);
	let definitionId = $state('quiz_demo');
	let hostEnabled = $state(true);
	let selectedDefinition = $state<GameDefinition | null>(null);
	let loadingDefinition = $state(false);
	const selectedDefinitionSummary = $derived(
		definitions.find((definition) => definition.id === definitionId) ?? null
	);

	onMount(async () => {
		const res = await fetch('/api/v1/definitions');
		if (!res.ok) {
			return;
		}
		definitions = await res.json();
		if (
			definitions.length > 0 &&
			!definitions.some((definition) => definition.id === definitionId)
		) {
			definitionId = definitions[0].id;
		}
		await loadDefinition(definitionId);
	});

	$effect(() => {
		if (!definitionId) {
			return;
		}
		void loadDefinition(definitionId);
	});

	async function loadDefinition(id: string) {
		loadingDefinition = true;
		const res = await fetch(`/api/v1/definitions/${id}`);
		if (!res.ok) {
			selectedDefinition = null;
			loadingDefinition = false;
			return;
		}
		selectedDefinition = await res.json();
		loadingDefinition = false;
	}

	async function createGame() {
		const res = await fetch('/api/v1/lobby/create', {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({
				definition_id: definitionId,
				host_enabled: hostEnabled
			})
		});
		const lobby: Lobby = await res.json();
		goto(`/host/${lobby.id}`);
	}
</script>

<svelte:head>
	<title>{$messages.create.title} | {$messages.common.appName}</title>
</svelte:head>

<div class="flex flex-wrap items-start justify-between gap-4">
	<div>
		<h1 class="page-title text-left">{$messages.create.title}</h1>
		<p class="page-subtitle text-left">{$messages.create.subtitle}</p>
	</div>
	<button class="btn btn-ghost text-lg" onclick={() => goto('/definitions')}
		>{$messages.common.manageDefinitions}</button
	>
</div>

<div class="stack-lg">
	<section class="card stack-md">
		<label class="input-wrap">
			<span class="label-title">{$messages.create.gameDefinition}</span>
			<div class="select-shell">
				<select bind:value={definitionId} class="input select-input text-lg">
					{#each definitions as definition}
						<option value={definition.id}>{definition.title}</option>
					{/each}
				</select>
				<span class="select-chevron" aria-hidden="true">▾</span>
			</div>
			{#if selectedDefinitionSummary}
				<p class="text-sm font-semibold text-slate-700">
					{$messages.common.selected}: {selectedDefinitionSummary.title}
				</p>
			{/if}
		</label>

		<label class="flex items-center justify-between gap-4 rounded-2xl bg-white/60 px-4 py-3">
			<div>
				<p class="label-title text-xl">{$messages.create.hostEnabledMode}</p>
				<p class="text-sm text-slate-600">{$messages.create.hostEnabledHelp}</p>
			</div>
			<input bind:checked={hostEnabled} type="checkbox" class="h-6 w-6" />
		</label>
	</section>

	<section class="card stack-md">
		<div class="flex items-start justify-between gap-4">
			<div>
				<h2 class="label-title text-2xl">{$messages.create.definitionPreview}</h2>
				{#if loadingDefinition}
					<p class="text-slate-500">{$messages.create.loadingDefinitionDetails}</p>
				{:else if selectedDefinition}
					<p class="text-slate-700">
						{selectedDefinition.description ?? $messages.create.noDescriptionProvided}
					</p>
				{:else}
					<p class="text-slate-500">{$messages.create.noDefinitionSelected}</p>
				{/if}
			</div>
			{#if selectedDefinition}
				<div class="rounded-2xl bg-sky-50 px-4 py-3 text-right">
					<p class="text-sm uppercase tracking-wide text-sky-700">{$messages.common.rounds}</p>
					<p class="text-3xl font-extrabold text-sky-900">{selectedDefinition.rounds.length}</p>
				</div>
			{/if}
		</div>

		{#if selectedDefinition}
			<div class="grid gap-3 md:grid-cols-2">
				{#each selectedDefinition.rounds as round}
					<div class="rounded-2xl bg-white/70 p-4">
						<h3 class="text-xl font-bold">{round.title ?? round.id}</h3>
						<p class="mt-1 text-sm text-slate-600">
							{round.steps.length}
							{$messages.common.steps}
						</p>
						<ul class="mt-3 space-y-2">
							{#each round.steps.slice(0, 3) as step}
								<li class="rounded-xl bg-slate-50 px-3 py-2">
									<div class="font-semibold">{step.title}</div>
									<div class="text-sm text-slate-600">
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

	<div class="flex flex-wrap gap-4">
		<button class="btn btn-ghost min-h-16 flex-1 text-2xl" onclick={() => goto('/')}>
			{$messages.common.back}
		</button>
		<button class="btn btn-primary min-h-16 flex-[2] text-3xl" onclick={createGame}
			>{$messages.common.createGame}</button
		>
	</div>
</div>
