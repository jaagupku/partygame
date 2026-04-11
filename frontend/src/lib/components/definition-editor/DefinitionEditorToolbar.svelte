<script lang="ts">
	import { tick } from 'svelte';

	type Props = {
		title: string;
		subtitle: string;
		editingTitle: boolean;
		saving: boolean;
		loadingEditor: boolean;
		onBack: () => void;
		onSave: () => void;
		onPreview: () => void;
		onAddStep: () => void;
		onAddRound: () => void;
		onOpenDetails: () => void;
		onStartTitleEdit: () => void;
		onFinishTitleEdit: () => void;
		onTitleChange: (value: string) => void;
	};

	let {
		title,
		subtitle,
		editingTitle,
		saving,
		loadingEditor,
		onBack,
		onSave,
		onPreview,
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
		<div class="flex items-center gap-3">
			<button class="btn btn-ghost px-4 py-2 text-sm" type="button" onclick={onBack}> Back </button>
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
						{title || 'Untitled Definition'}
					</h1>
				</button>
			{/if}
		</div>
		<p class="mt-1 text-sm text-slate-500">{subtitle}</p>
	</div>

	<div class="flex flex-wrap items-center gap-2">
		<button class="btn btn-accent px-4 py-2 text-sm" type="button" onclick={onAddRound}>
			New Round
		</button>
		<button class="btn btn-primary px-4 py-2 text-sm" type="button" onclick={onAddStep}>
			New Step
		</button>
		<button class="btn btn-ghost px-4 py-2 text-sm" type="button" onclick={onOpenDetails}>
			Definition Details
		</button>
		<button class="btn btn-ghost px-4 py-2 text-sm" type="button" onclick={onPreview}>
			Preview
		</button>
		<button
			class="btn btn-primary px-5 py-2 text-sm"
			type="button"
			onclick={onSave}
			disabled={saving || loadingEditor}
		>
			{saving ? 'Saving...' : 'Save'}
		</button>
	</div>
</div>
