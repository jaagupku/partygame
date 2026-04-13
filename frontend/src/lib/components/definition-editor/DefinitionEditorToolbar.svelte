<script lang="ts">
	import { tick } from 'svelte';
	import { messages } from '$lib/i18n';

	type Props = {
		title: string;
		breadcrumbCurrentLabel: string;
		editingTitle: boolean;
		saving: boolean;
		loadingEditor: boolean;
		onGoHome: () => void;
		onManageDefinitions: () => void;
		onSave: () => void;
		onAddStep: () => void;
		onAddRound: () => void;
		onOpenDetails: () => void;
		onStartTitleEdit: () => void;
		onFinishTitleEdit: () => void;
		onTitleChange: (value: string) => void;
	};

	let {
		title,
		breadcrumbCurrentLabel,
		editingTitle,
		saving,
		loadingEditor,
		onGoHome,
		onManageDefinitions,
		onSave,
		onAddStep,
		onAddRound,
		onOpenDetails,
		onStartTitleEdit,
		onFinishTitleEdit,
		onTitleChange
	}: Props = $props();

	let titleInput = $state<HTMLInputElement | null>(null);

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
	class="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 bg-white/80 px-5 py-4"
>
	<div class="min-w-0 flex-1">
		<nav
			class="mb-2 flex flex-wrap items-center gap-2 text-sm text-slate-500"
			aria-label={$messages.common.breadcrumb}
		>
			<button class="transition hover:text-slate-700" type="button" onclick={onGoHome}
				>{$messages.common.home}</button
			>
			<span aria-hidden="true">/</span>
			<button class="transition hover:text-slate-700" type="button" onclick={onManageDefinitions}>
				{$messages.common.manageDefinitions}
			</button>
			<span aria-hidden="true">/</span>
			<span aria-current="page" class="font-semibold text-slate-700">{breadcrumbCurrentLabel}</span>
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
					<h1 class="truncate text-3xl font-extrabold text-slate-900">
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
		<button
			class="btn btn-primary px-5 py-2 text-sm"
			type="button"
			onclick={onSave}
			disabled={saving || loadingEditor}
		>
			{saving ? $messages.editor.saving : $messages.common.save}
		</button>
	</div>
</div>
