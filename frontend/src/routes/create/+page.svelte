<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';

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
	<title>Create Game | Party Game</title>
</svelte:head>

<div class="flex flex-wrap items-start justify-between gap-4">
	<div>
		<h1 class="page-title text-left">Create Game</h1>
		<p class="page-subtitle text-left">
			Pick a definition, review it, and choose whether a host phone runs the show.
		</p>
	</div>
	<button class="btn btn-ghost text-lg" onclick={() => goto('/definitions')}
		>Manage Definitions</button
	>
</div>

<div class="stack-lg">
	<section class="card stack-md">
		<label class="input-wrap">
			<span class="label-title">Game definition</span>
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
					Selected: {selectedDefinitionSummary.title}
				</p>
			{/if}
		</label>

		<label class="flex items-center justify-between gap-4 rounded-2xl bg-white/60 px-4 py-3">
			<div>
				<p class="label-title text-xl">Host-enabled mode</p>
				<p class="text-sm text-slate-600">
					When on, the first joined player becomes the host controller.
				</p>
			</div>
			<input bind:checked={hostEnabled} type="checkbox" class="h-6 w-6" />
		</label>
	</section>

	<section class="card stack-md">
		<div class="flex items-start justify-between gap-4">
			<div>
				<h2 class="label-title text-2xl">Definition Preview</h2>
				{#if loadingDefinition}
					<p class="text-slate-500">Loading definition details...</p>
				{:else if selectedDefinition}
					<p class="text-slate-700">
						{selectedDefinition.description ?? 'No description provided.'}
					</p>
				{:else}
					<p class="text-slate-500">No definition selected.</p>
				{/if}
			</div>
			{#if selectedDefinition}
				<div class="rounded-2xl bg-sky-50 px-4 py-3 text-right">
					<p class="text-sm uppercase tracking-wide text-sky-700">Rounds</p>
					<p class="text-3xl font-extrabold text-sky-900">{selectedDefinition.rounds.length}</p>
				</div>
			{/if}
		</div>

		{#if selectedDefinition}
			<div class="grid gap-3 md:grid-cols-2">
				{#each selectedDefinition.rounds as round}
					<div class="rounded-2xl bg-white/70 p-4">
						<h3 class="text-xl font-bold">{round.title ?? round.id}</h3>
						<p class="mt-1 text-sm text-slate-600">{round.steps.length} steps</p>
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
		<button class="btn btn-ghost min-h-16 flex-1 text-2xl" onclick={() => goto('/')}>Back</button>
		<button class="btn btn-primary min-h-16 flex-[2] text-3xl" onclick={createGame}
			>Create Game</button
		>
	</div>
</div>
