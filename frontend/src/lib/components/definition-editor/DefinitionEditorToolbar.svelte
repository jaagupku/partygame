<script lang="ts">
	import { tick } from 'svelte';
	import { messages } from '$lib/i18n';

	type Props = {
		title: string;
		breadcrumbCurrentLabel: string;
		editingTitle: boolean;
		saving: boolean;
		exporting: boolean;
		importing: boolean;
		loadingEditor: boolean;
		onGoHome: () => void;
		onManageDefinitions: () => void;
		onSave: () => void;
		onExport?: () => void;
		onImport: (event: Event) => void;
		onAddStep: () => void;
		onAddRound: () => void;
		onOpenDetails: () => void;
		onDelete?: () => void;
		onStartTitleEdit: () => void;
		onFinishTitleEdit: () => void;
		onTitleChange: (value: string) => void;
	};

	let {
		title,
		breadcrumbCurrentLabel,
		editingTitle,
		saving,
		exporting,
		importing,
		loadingEditor,
		onGoHome,
		onManageDefinitions,
		onSave,
		onExport,
		onImport,
		onAddStep,
		onAddRound,
		onOpenDetails,
		onDelete,
		onStartTitleEdit,
		onFinishTitleEdit,
		onTitleChange
	}: Props = $props();

	let titleInput = $state<HTMLInputElement | null>(null);
	let importInput = $state<HTMLInputElement | null>(null);

	$effect(() => {
		if (!editingTitle || !titleInput) {
			return;
		}
		tick().then(() => {
			titleInput?.focus();
			titleInput?.select();
		});
	});
</script>

<div
	class="theme-surface-raised flex flex-wrap items-center justify-between gap-4 border-b px-5 py-4"
>
	<div class="min-w-0 flex-1">
		<nav
			class="editor-text-muted mb-2 flex flex-wrap items-center gap-2 text-sm"
			aria-label={$messages.common.breadcrumb}
		>
			<button class="transition hover:opacity-80" type="button" onclick={onGoHome}
				>{$messages.common.home}</button
			>
			<span aria-hidden="true">/</span>
			<button class="transition hover:opacity-80" type="button" onclick={onManageDefinitions}>
				{$messages.common.manageDefinitions}
			</button>
			<span aria-hidden="true">/</span>
			<span aria-current="page" class="editor-text font-semibold">{breadcrumbCurrentLabel}</span>
		</nav>
		<div class="flex flex-wrap items-center gap-3">
			{#if editingTitle}
				<input
					bind:this={titleInput}
					value={title}
					class="input max-w-xl text-2xl font-extrabold"
					oninput={(event) => onTitleChange((event.currentTarget as HTMLInputElement).value)}
					onblur={onFinishTitleEdit}
					onkeydown={(event) => {
						if (event.key === 'Enter' || event.key === 'Escape') {
							onFinishTitleEdit();
						}
					}}
				/>
			{:else}
				<button class="min-w-0 text-left" type="button" onclick={onStartTitleEdit}>
					<h1 class="editor-text truncate text-3xl font-extrabold">
						{title || $messages.definitions.untitledDefinition}
					</h1>
				</button>
			{/if}
		</div>
	</div>

	<div class="flex flex-wrap items-center gap-2">
		<button class="btn btn-accent px-4 py-2 text-sm" type="button" onclick={onAddRound}>
			{$messages.editor.newRound}
		</button>
		<button class="btn btn-primary px-4 py-2 text-sm" type="button" onclick={onAddStep}>
			{$messages.editor.newStep}
		</button>
		<button class="btn btn-ghost px-4 py-2 text-sm" type="button" onclick={onOpenDetails}>
			{$messages.editor.definitionDetails}
		</button>
		{#if onDelete}
			<button class="btn btn-danger-soft px-4 py-2 text-sm" type="button" onclick={onDelete}>
				{$messages.common.remove}
			</button>
		{/if}
		<button
			class="btn btn-primary px-5 py-2 text-sm"
			type="button"
			onclick={onSave}
			disabled={saving || loadingEditor}
		>
			{saving ? $messages.editor.saving : $messages.common.save}
		</button>
		{#if onExport}
			<button
				class="btn btn-ghost px-4 py-2 text-sm"
				type="button"
				onclick={onExport}
				disabled={exporting || loadingEditor}
			>
				{exporting ? $messages.editor.exportingDefinition : $messages.editor.exportDefinition}
			</button>
		{/if}
		<button
			class="btn btn-ghost px-4 py-2 text-sm"
			type="button"
			onclick={() => importInput?.click()}
			disabled={importing || loadingEditor}
		>
			{importing ? $messages.editor.importingDefinition : $messages.editor.importDefinition}
		</button>
		<input
			bind:this={importInput}
			class="hidden"
			type="file"
			accept=".zip,application/zip"
			onchange={onImport}
		/>
	</div>
</div>
