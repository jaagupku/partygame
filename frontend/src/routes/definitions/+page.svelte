<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';

	let definitions = $state<DefinitionSummary[]>([]);
	let loading = $state(false);
	let errorMessage = $state('');

	onMount(async () => {
		loading = true;
		const response = await fetch('/api/v1/definitions');
		loading = false;
		if (!response.ok) {
			errorMessage = 'Could not load definitions.';
			return;
		}
		definitions = await response.json();
	});
</script>

<svelte:head>
	<title>Manage Definitions | Party Game</title>
</svelte:head>

<div class="flex flex-wrap items-start justify-between gap-4">
	<div>
		<nav
			class="mb-2 flex flex-wrap items-center gap-2 text-sm text-slate-500"
			aria-label="Breadcrumb"
		>
			<button class="transition hover:text-slate-700" onclick={() => goto('/')}>Home</button>
			<span aria-hidden="true">/</span>
			<span aria-current="page" class="font-semibold text-slate-700">Manage Definitions</span>
		</nav>
		<h1 class="page-title text-left">Manage Definitions</h1>
		<p class="page-subtitle text-left">
			Browse your saved game definitions and jump into the editor when you want to create or update
			one.
		</p>
	</div>
	<div class="flex flex-wrap gap-3">
		<button class="btn btn-ghost text-lg" onclick={() => goto('/')}>Home</button>
		<button class="btn btn-ghost text-lg" onclick={() => goto('/create')}>Create Game</button>
		<button class="btn btn-accent text-lg" onclick={() => goto('/definitions/new')}
			>Create Definition</button
		>
	</div>
</div>

<div class="stack-lg">
	<section class="card stack-md">
		<div class="flex items-center justify-between gap-3">
			<h2 class="label-title text-2xl">Current Definitions</h2>
			{#if loading}
				<span class="text-sm text-slate-500">Loading...</span>
			{/if}
		</div>

		{#if errorMessage}
			<div class="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-red-700">
				{errorMessage}
			</div>
		{:else if definitions.length === 0}
			<div class="rounded-3xl border border-dashed border-slate-300 bg-slate-50/80 p-8 text-center">
				<h3 class="text-2xl font-bold text-slate-800">No Definitions Yet</h3>
				<p class="mt-2 text-slate-600">
					Create your first definition to start building rounds and slides.
				</p>
				<button class="btn btn-primary mt-4" onclick={() => goto('/definitions/new')}
					>Create Definition</button
				>
			</div>
		{:else}
			<div class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
				{#each definitions as definition}
					<div class="rounded-3xl border border-slate-200 bg-white/80 p-4 shadow-sm">
						<div class="flex items-start justify-between gap-3">
							<div>
								<h3 class="text-xl font-bold text-slate-900">{definition.title}</h3>
								<p class="mt-1 text-sm text-slate-500">{definition.id}</p>
							</div>
							<span class="badge bg-sky-100 text-sky-800">Definition</span>
						</div>

						<p class="mt-3 min-h-12 text-sm text-slate-600">
							{definition.description ?? 'No description provided yet.'}
						</p>

						<div class="mt-4 flex flex-wrap gap-2">
							<button
								class="btn btn-primary flex-1 px-4 py-2 text-sm"
								onclick={() => goto(`/definitions/${definition.id}`)}
							>
								Edit
							</button>
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</section>
</div>
