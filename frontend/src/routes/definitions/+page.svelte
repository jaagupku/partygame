<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { currentUser } from '$lib/auth-store';
	import { downloadBlob } from '$lib/browser-download.js';
	import { encodeDefinitionIdForPath } from '$lib/definition-paths.js';
	import { canEditDefinitionForUser } from '$lib/definition-permissions.js';
	import { readErrorDetail } from '$lib/http-errors.js';
	import { messages } from '$lib/i18n';
	import { showErrorToast, showSuccessToast } from '$lib/toast-store';

	let definitions = $state<DefinitionSummary[]>([]);
	let loading = $state(false);
	let exportingDefinitionId = $state<string | null>(null);
	let importing = $state(false);
	let loadFailed = $state(false);
	let importInput = $state<HTMLInputElement | null>(null);

	function visibilityLabel(visibility: DefinitionVisibility) {
		if (visibility === 'private') {
			return $messages.definitions.visibilityPrivate;
		}
		if (visibility === 'login_required') {
			return $messages.definitions.visibilityLoginRequired;
		}
		return $messages.definitions.visibilityPublic;
	}

	onMount(loadDefinitions);

	async function loadDefinitions() {
		loading = true;
		loadFailed = false;
		const response = await fetch('/api/v1/definitions');
		loading = false;
		if (!response.ok) {
			loadFailed = true;
			showErrorToast($messages.definitions.couldNotLoadDefinitions);
			return;
		}
		definitions = await response.json();
	}

	async function exportDefinition(definitionId: string) {
		exportingDefinitionId = definitionId;
		const response = await fetch(
			`/api/v1/definitions/${encodeDefinitionIdForPath(definitionId)}/export`
		);
		exportingDefinitionId = null;
		if (!response.ok) {
			showErrorToast(
				(await readErrorDetail(response)) || $messages.definitions.couldNotExportDefinition
			);
			return;
		}
		downloadBlob(await response.blob(), `${definitionId}.zip`);
		showSuccessToast($messages.definitions.definitionExported);
	}

	async function importDefinition(event: Event) {
		const input = event.currentTarget as HTMLInputElement;
		const file = input.files?.[0];
		if (!file) {
			return;
		}
		importing = true;
		const response = await fetch('/api/v1/definitions/import', {
			method: 'POST',
			headers: {
				'Content-Type': file.type || 'application/zip'
			},
			body: file
		});
		importing = false;
		input.value = '';
		if (!response.ok) {
			showErrorToast(
				(await readErrorDetail(response)) || $messages.definitions.couldNotImportDefinition
			);
			return;
		}
		const importedDefinition = (await response.json()) as GameDefinition;
		showSuccessToast($messages.definitions.definitionImported);
		goto(`/definitions/${encodeDefinitionIdForPath(importedDefinition.id)}`);
	}
</script>

<svelte:head>
	<title>{$messages.definitions.title} | {$messages.common.appName}</title>
</svelte:head>

<div class="flex flex-wrap items-start justify-between gap-4">
	<div>
		<h1 class="page-title text-left">{$messages.definitions.title}</h1>
		<p class="page-subtitle text-left">{$messages.definitions.subtitle}</p>
	</div>
	<div class="flex flex-wrap gap-3">
		<button class="btn btn-ghost text-lg" onclick={() => goto('/create')}>
			{$messages.common.createGame}
		</button>
		{#if $currentUser}
			<button
				class="btn btn-ghost text-lg"
				type="button"
				onclick={() => importInput?.click()}
				disabled={importing}
			>
				{importing ? $messages.editor.importingDefinition : $messages.editor.importDefinition}
			</button>
			<input
				bind:this={importInput}
				class="hidden"
				type="file"
				accept=".zip,application/zip"
				onchange={importDefinition}
			/>
			<button class="btn btn-accent text-lg" onclick={() => goto('/definitions/new')}
				>{$messages.common.createDefinition}</button
			>
		{:else}
			<button class="btn btn-accent text-lg" onclick={() => goto('/login')}
				>{$messages.auth.login}</button
			>
		{/if}
	</div>
</div>

<div class="stack-lg">
	<section class="card stack-md library-section">
		<div class="flex items-center justify-between gap-3">
			<h2 class="label-title text-2xl">{$messages.definitions.currentDefinitions}</h2>
			{#if loading}
				<span class="text-sm" style="color: var(--party-subtle)">{$messages.common.loading}</span>
			{/if}
		</div>

		{#if !loadFailed && definitions.length === 0}
			<div class="library-empty rounded-3xl border border-dashed p-8 text-center">
				<h3 class="text-2xl font-bold">{$messages.definitions.noDefinitionsYet}</h3>
				<p class="mt-2">{$messages.definitions.noDefinitionsHelp}</p>
				{#if $currentUser}
					<button class="btn btn-primary mt-4" onclick={() => goto('/definitions/new')}
						>{$messages.common.createDefinition}</button
					>
				{:else}
					<p class="mt-3 text-sm font-semibold">
						{$messages.definitions.signInToCreate}
					</p>
				{/if}
			</div>
		{:else if !loadFailed}
			<div class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
				{#each definitions as definition}
					<div class="definition-library-card rounded-3xl border p-4 shadow-sm">
						<div class="flex items-start justify-between gap-3">
							<div>
								<h3 class="text-xl font-bold">{definition.title}</h3>
								<p class="mt-1 text-sm">{definition.id}</p>
							</div>
							<span class="library-visibility-badge badge"
								>{visibilityLabel(definition.visibility)}</span
							>
						</div>
						{#if definition.owner_display_name}
							<p class="mt-2 text-xs font-semibold uppercase tracking-wide">
								{$messages.definitions.owner}: {definition.owner_display_name}
							</p>
						{/if}

						<p class="mt-3 min-h-12 text-sm">
							{definition.description ?? $messages.definitions.noDescriptionProvidedYet}
						</p>

						<div class="mt-4 flex flex-wrap gap-2">
							{#if canEditDefinitionForUser(definition, $currentUser)}
								<button
									class="btn btn-primary flex-1 px-4 py-2 text-sm"
									onclick={() => goto(`/definitions/${encodeDefinitionIdForPath(definition.id)}`)}
								>
									{$messages.common.edit}
								</button>
							{/if}
							<button
								class="btn btn-ghost flex-1 px-4 py-2 text-sm"
								type="button"
								onclick={() => exportDefinition(definition.id)}
								disabled={exportingDefinitionId === definition.id}
							>
								{exportingDefinitionId === definition.id
									? $messages.editor.exportingDefinition
									: $messages.editor.exportDefinition}
							</button>
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</section>
</div>

<style lang="postcss">
	.library-section,
	.definition-library-card,
	.library-empty {
		border-color: var(--party-border);
		background: var(--party-surface-strong);
		color: var(--party-ink);
	}

	.definition-library-card p,
	.library-empty p {
		color: var(--party-subtle);
	}

	.library-visibility-badge {
		border: 1px solid var(--party-soft-primary-border);
		background: var(--party-soft-primary-bg);
		color: var(--party-soft-primary-text);
	}
</style>
